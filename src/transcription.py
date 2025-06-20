"""
Audio transcription service using AssemblyAI
"""

import logging
import time
from pathlib import Path
from typing import Dict

import assemblyai as aai

from .config import TranscriptionConfig


class TranscriptionService:
    """Handles audio transcription using AssemblyAI"""
    
    def __init__(self, config: TranscriptionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        if config.service != "assemblyai":
            raise ValueError(f"Unsupported transcription service: {config.service}")
        
        aai.settings.api_key = config.api_key
        
        # Configure transcription settings optimized for voice memos
        self.transcription_config = aai.TranscriptionConfig(
            speaker_labels=True,
            format_text=True,
            punctuate=True,
            disfluencies=True,
            speech_model=aai.SpeechModel.best,
            language_code="en_us"
        )
        
        self.client = aai.Transcriber(config=self.transcription_config)
        
        self.logger.info("Initialized AssemblyAI transcription service")
    
    def transcribe(self, audio_path: Path) -> Dict:
        """Transcribe audio file and return transcript with metadata"""
        self.logger.info(f"Starting transcription of: {audio_path.name}")
        
        try:
            # Submit transcription job (this will wait for completion)
            transcript = self.client.transcribe(str(audio_path))
            
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"Transcription failed: {transcript.error}")
            
            # Extract transcript data
            result = {
                'text': transcript.text,
                'confidence': getattr(transcript, 'confidence', 0.0),
                'audio_duration': getattr(transcript, 'audio_duration', 0),
                'language_code': 'en_us',  # We set this explicitly in config
                'words': [],
                'sentences': []
            }
            
            # Add word-level timestamps if available
            if transcript.words:
                result['words'] = [
                    {
                        'text': word.text,
                        'start': word.start,
                        'end': word.end,
                        'confidence': word.confidence
                    }
                    for word in transcript.words
                ]
            
            # Add sentence-level information
            if hasattr(transcript, 'sentences') and transcript.sentences:
                result['sentences'] = [
                    {
                        'text': sentence.text,
                        'start': sentence.start,
                        'end': sentence.end
                    }
                    for sentence in transcript.sentences
                ]
            
            self.logger.info(f"Transcription completed: {len(result['text'])} characters")
            return result
            
        except Exception as e:
            self.logger.error(f"Transcription failed for {audio_path.name}: {e}")
            raise Exception(f"Failed to transcribe audio: {e}")
    
    def format_transcript_for_output(self, transcript_data: Dict) -> str:
        """Format transcript data for markdown output"""
        lines = [
            "# Raw Transcript",
            "",
            f"**Duration:** {transcript_data.get('audio_duration', 'Unknown')} ms",
            f"**Language:** {transcript_data.get('language_code', 'Unknown')}",
            f"**Confidence:** {transcript_data.get('confidence', 'Unknown'):.2f}",
            "",
            "## Transcript Text",
            "",
            transcript_data['text'],
            ""
        ]
        
        # Add word-level timestamps if available
        if transcript_data.get('words'):
            lines.extend([
                "## Word-Level Timestamps",
                "",
                "| Word | Start (ms) | End (ms) | Confidence |",
                "|------|------------|----------|------------|"
            ])
            
            for word in transcript_data['words'][:50]:  # Limit to first 50 words
                lines.append(
                    f"| {word['text']} | {word['start']} | {word['end']} | {word['confidence']:.2f} |"
                )
            
            if len(transcript_data['words']) > 50:
                lines.append("| ... | ... | ... | ... |")
            
            lines.append("")
        
        return "\n".join(lines)