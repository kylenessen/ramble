"""
LLM processing service for content enhancement and topic separation
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import openai
from anthropic import Anthropic

from .config import LLMConfig


class LLMProcessor:
    """Handles LLM processing for transcript enhancement and topic separation"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        if config.service == "openai":
            self.client = openai.OpenAI(api_key=config.api_key)
        elif config.service == "openrouter":
            self.client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=config.api_key
            )
        elif config.service == "claude":
            self.client = Anthropic(api_key=config.api_key)
        else:
            raise ValueError(f"Unsupported LLM service: {config.service}")
        
        self.logger.info(f"Initialized {config.service} LLM processor")
    
    def process_transcript(self, transcript_data: Dict, file_created_time: Optional[datetime] = None) -> Dict:
        """Process transcript through LLM for enhancement and topic separation"""
        self.logger.info("Processing transcript with LLM")
        
        prompt = self._build_prompt(transcript_data['text'], file_created_time)
        
        try:
            if self.config.service in ["openai", "openrouter"]:
                response = self._process_with_openai(prompt)
            elif self.config.service == "claude":
                response = self._process_with_claude(prompt)
            else:
                raise ValueError(f"Unsupported service: {self.config.service}")
            
            processed_content = self._parse_response(response)
            content_length = len(processed_content['content'])
            self.logger.info(f"LLM processing completed: {content_length} characters of organized content")
            
            return processed_content
            
        except Exception as e:
            self.logger.error(f"LLM processing failed: {e}")
            raise Exception(f"Failed to process transcript with LLM: {e}")
    
    def _build_prompt(self, transcript_text: str, file_created_time: Optional[datetime] = None) -> str:
        """Build the prompt for LLM processing"""
        return f"""Process this voice memo transcript into a single, organized document:

ORIGINAL TRANSCRIPT:
{transcript_text}

Please:
1. **CLEAN**: Remove filler words (um, uh, like, you know) and fix transcription artifacts (run-on sentences, missing punctuation, capitalization) while preserving the speaker's natural voice and intent
2. **EXCLUDE**: Remove any irrelevant interactions like talking to pets (e.g., "Angus, hurry up"), greeting neighbors, or other incidental conversations that aren't part of the main content
3. **STRUCTURE**: Organize content with clear headings where applicable. If there is a single idea, use only one heading
4. **PRESERVE FLOW**: Maintain the natural progression of topics and the speaker's original meaning
5. **COMPLETE**: Naturally finish any incomplete thoughts without adding new ideas
6. Create concise session title reflecting the main topic 

Format response as JSON:
{{
  "session_title": "descriptive-session-title",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "content": "# Session Title\n\nWell-structured markdown content with headings, organized thoughts, and actionable items"
}}

Ensure the JSON is valid and properly formatted."""
    
    def _process_with_openai(self, prompt: str) -> str:
        """Process prompt with OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are an expert at processing voice memos into structured, actionable content. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=8000
        )
        
        return response.choices[0].message.content
    
    def _process_with_claude(self, prompt: str) -> str:
        """Process prompt with Anthropic Claude API"""
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=8000,
            temperature=0.5,
            system="You are an expert at processing voice memos into structured, actionable content. Always respond with valid JSON.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
    
    def _parse_response(self, response: str) -> Dict:
        """Parse and validate LLM response"""
        try:
            # Try to extract JSON from response (in case there's extra text)
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            # Validate structure
            required_fields = ['session_title', 'keywords', 'content']
            for field in required_fields:
                if field not in parsed:
                    raise ValueError(f"Missing required field: {field}")
            
            if not isinstance(parsed['content'], str) or len(parsed['content'].strip()) == 0:
                raise ValueError("Content must be a non-empty string")
            
            if not isinstance(parsed['keywords'], list):
                raise ValueError("Keywords must be a list")
            
            return parsed
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in LLM response: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse LLM response: {e}")
    
    def _clean_filename(self, filename: str) -> str:
        """Clean and validate filename"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '-')
        
        # Limit length
        if len(filename) > 40:
            filename = filename[:37] + "..."
        
        # Ensure it ends with .md
        if not filename.endswith('.md'):
            filename += '.md'
        
        return filename