#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音声処理モジュール
音声ファイルから会話部分を抽出し、無音・ノイズを除去して軽量化する
"""

import os
import json
import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np

# 音声処理ライブラリ
try:
    import librosa
    import soundfile as sf
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
except ImportError as e:
    print(f"必要なライブラリがインストールされていません: {e}")
    print("以下のコマンドでインストールしてください:")
    print("pip install librosa soundfile pydub")
    
from utils.logger import Logger

class AudioProcessor:
    """音声ファイル処理クラス"""
    
    def __init__(self, config_path: str = "config/settings.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.logger = Logger("AudioProcessor")
        self.config = self._load_config(config_path)
        
        # 処理パラメータ
        self.silence_threshold = self.config.get('audio_processing', {}).get('silence_threshold', -40)  # dB
        self.min_silence_duration = self.config.get('audio_processing', {}).get('min_silence_duration', 2000)  # ms
        self.chunk_size = self.config.get('audio_processing', {}).get('chunk_size', 600)  # 10分ごとのチャンク（秒）
        self.target_sample_rate = self.config.get('audio_processing', {}).get('target_sample_rate', 16000)  # Hz
        self.target_bitrate = self.config.get('audio_processing', {}).get('target_bitrate', '64k')  # ビットレート
        
        # 一時ファイル保存先
        self.temp_dir = Path(self.config.get('local_storage', {}).get('temp_dir', '/tmp/audio_processing'))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 処理済みファイル保存先
        self.processed_dir = Path(self.config.get('local_storage', {}).get('processed_dir', 'processed_audio'))
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("音声処理モジュールを初期化しました")
    
    def _load_config(self, config_path: str) -> Dict:
        """設定ファイルを読み込む"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"設定ファイル読み込みエラー: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """デフォルト設定を返す"""
        return {
            'audio_processing': {
                'silence_threshold': -40,
                'min_silence_duration': 2000,
                'chunk_size': 600,
                'target_sample_rate': 16000,
                'target_bitrate': '64k'
            },
            'local_storage': {
                'temp_dir': '/tmp/audio_processing',
                'processed_dir': 'processed_audio'
            }
        }
    
    def process_audio_file(self, input_path: str, output_dir: Optional[str] = None) -> Optional[str]:
        """
        音声ファイルを処理して軽量化
        
        Args:
            input_path: 入力音声ファイルのパス
            output_dir: 出力ディレクトリ（省略時はデフォルト）
        
        Returns:
            処理済みファイルのパス
        """
        try:
            input_path = Path(input_path)
            if not input_path.exists():
                self.logger.error(f"入力ファイルが存在しません: {input_path}")
                return None
            
            self.logger.info(f"音声処理開始: {input_path.name}")
            
            # 出力ディレクトリの決定
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
            else:
                output_dir = self.processed_dir
            
            # ファイルサイズチェック
            original_size = input_path.stat().st_size
            self.logger.info(f"元のファイルサイズ: {self._format_size(original_size)}")
            
            # 1. 音声ファイルを読み込み
            audio = AudioSegment.from_file(str(input_path))
            
            # 2. モノラル変換（ステレオの場合）
            if audio.channels > 1:
                self.logger.info("ステレオからモノラルに変換中...")
                audio = audio.set_channels(1)
            
            # 3. サンプルレート変換
            if audio.frame_rate != self.target_sample_rate:
                self.logger.info(f"サンプルレートを{audio.frame_rate}Hzから{self.target_sample_rate}Hzに変換中...")
                audio = audio.set_frame_rate(self.target_sample_rate)
            
            # 4. 無音部分を検出して除去
            self.logger.info("無音部分を検出中...")
            nonsilent_chunks = detect_nonsilent(
                audio,
                min_silence_len=self.min_silence_duration,
                silence_thresh=self.silence_threshold
            )
            
            if not nonsilent_chunks:
                self.logger.warning("音声が検出されませんでした")
                return None
            
            # 5. 音声部分のみを結合
            self.logger.info(f"音声部分を抽出中... (検出された区間: {len(nonsilent_chunks)})")
            processed_audio = AudioSegment.empty()
            
            for start_ms, end_ms in nonsilent_chunks:
                # 前後に少しマージンを追加（カット感を減らすため）
                margin = 100  # ms
                start_ms = max(0, start_ms - margin)
                end_ms = min(len(audio), end_ms + margin)
                processed_audio += audio[start_ms:end_ms]
            
            # 6. 音量正規化
            self.logger.info("音量を正規化中...")
            target_dBFS = -20.0
            change_in_dBFS = target_dBFS - processed_audio.dBFS
            processed_audio = processed_audio.apply_gain(change_in_dBFS)
            
            # 7. 出力ファイル名の生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{input_path.stem}_processed_{timestamp}.mp3"
            output_path = output_dir / output_filename
            
            # 8. エクスポート（圧縮）
            self.logger.info(f"処理済み音声を保存中: {output_path}")
            processed_audio.export(
                str(output_path),
                format="mp3",
                bitrate=self.target_bitrate,
                parameters=["-ac", "1"]  # モノラル
            )
            
            # 処理結果の確認
            processed_size = output_path.stat().st_size
            compression_ratio = (1 - processed_size / original_size) * 100
            
            self.logger.info(f"処理完了:")
            self.logger.info(f"  - 元のサイズ: {self._format_size(original_size)}")
            self.logger.info(f"  - 処理後サイズ: {self._format_size(processed_size)}")
            self.logger.info(f"  - 圧縮率: {compression_ratio:.1f}%削減")
            self.logger.info(f"  - 元の長さ: {len(audio) / 1000:.1f}秒")
            self.logger.info(f"  - 処理後の長さ: {len(processed_audio) / 1000:.1f}秒")
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"音声処理エラー: {e}", exc_info=True)
            return None
    
    def process_batch(self, input_files: List[str], output_dir: Optional[str] = None) -> List[str]:
        """
        複数の音声ファイルをバッチ処理
        
        Args:
            input_files: 入力ファイルのリスト
            output_dir: 出力ディレクトリ
        
        Returns:
            処理済みファイルのパスリスト
        """
        processed_files = []
        total = len(input_files)
        
        for i, input_file in enumerate(input_files, 1):
            self.logger.info(f"バッチ処理 [{i}/{total}]: {Path(input_file).name}")
            
            result = self.process_audio_file(input_file, output_dir)
            if result:
                processed_files.append(result)
            else:
                self.logger.warning(f"処理をスキップ: {input_file}")
        
        self.logger.info(f"バッチ処理完了: {len(processed_files)}/{total} ファイル処理済み")
        return processed_files
    
    def extract_voice_activity(self, input_path: str) -> Optional[Dict]:
        """
        Voice Activity Detection (VAD) を使用して音声活動を分析
        
        Args:
            input_path: 入力音声ファイルのパス
        
        Returns:
            音声活動の統計情報
        """
        try:
            audio = AudioSegment.from_file(input_path)
            
            # 無音部分を検出
            nonsilent_chunks = detect_nonsilent(
                audio,
                min_silence_len=self.min_silence_duration,
                silence_thresh=self.silence_threshold
            )
            
            # 統計情報を計算
            total_duration = len(audio) / 1000  # 秒
            voice_duration = sum((end - start) for start, end in nonsilent_chunks) / 1000  # 秒
            silence_duration = total_duration - voice_duration
            voice_ratio = (voice_duration / total_duration * 100) if total_duration > 0 else 0
            
            stats = {
                'total_duration': total_duration,
                'voice_duration': voice_duration,
                'silence_duration': silence_duration,
                'voice_ratio': voice_ratio,
                'num_segments': len(nonsilent_chunks),
                'segments': [(start/1000, end/1000) for start, end in nonsilent_chunks[:10]]  # 最初の10セグメント
            }
            
            self.logger.info(f"VAD分析完了: 音声割合 {voice_ratio:.1f}%")
            return stats
            
        except Exception as e:
            self.logger.error(f"VAD分析エラー: {e}")
            return None
    
    def split_long_audio(self, input_path: str, chunk_duration: int = 600) -> List[str]:
        """
        長い音声ファイルをチャンクに分割
        
        Args:
            input_path: 入力音声ファイルのパス
            chunk_duration: チャンクの長さ（秒）
        
        Returns:
            分割されたファイルのパスリスト
        """
        try:
            input_path = Path(input_path)
            audio = AudioSegment.from_file(str(input_path))
            
            chunk_length_ms = chunk_duration * 1000
            chunks = []
            
            # チャンクに分割
            for i, start_ms in enumerate(range(0, len(audio), chunk_length_ms)):
                end_ms = min(start_ms + chunk_length_ms, len(audio))
                chunk = audio[start_ms:end_ms]
                
                # チャンクを保存
                chunk_path = self.temp_dir / f"{input_path.stem}_chunk_{i:03d}.mp3"
                chunk.export(str(chunk_path), format="mp3", bitrate=self.target_bitrate)
                chunks.append(str(chunk_path))
                
                self.logger.info(f"チャンク {i+1} を作成: {start_ms/1000:.1f}秒 - {end_ms/1000:.1f}秒")
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"音声分割エラー: {e}")
            return []
    
    def merge_audio_files(self, input_files: List[str], output_path: str) -> bool:
        """
        複数の音声ファイルを結合
        
        Args:
            input_files: 入力ファイルのリスト
            output_path: 出力ファイルのパス
        
        Returns:
            成功したかどうか
        """
        try:
            combined = AudioSegment.empty()
            
            for file_path in input_files:
                self.logger.info(f"結合中: {Path(file_path).name}")
                audio = AudioSegment.from_file(file_path)
                combined += audio
            
            combined.export(output_path, format="mp3", bitrate=self.target_bitrate)
            self.logger.info(f"結合完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"音声結合エラー: {e}")
            return False
    
    def _format_size(self, size_bytes: int) -> str:
        """ファイルサイズを人間が読みやすい形式に変換"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def cleanup_temp_files(self):
        """一時ファイルをクリーンアップ"""
        try:
            for temp_file in self.temp_dir.glob("*"):
                if temp_file.is_file():
                    temp_file.unlink()
                    self.logger.debug(f"一時ファイル削除: {temp_file.name}")
            self.logger.info("一時ファイルのクリーンアップ完了")
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")


if __name__ == "__main__":
    # テスト実行
    processor = AudioProcessor()
    
    # テストファイルのパス（実際のパスに置き換えてください）
    test_file = "/path/to/test/audio.mp3"
    
    if os.path.exists(test_file):
        # VAD分析
        stats = processor.extract_voice_activity(test_file)
        if stats:
            print(f"音声統計: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
        # 音声処理
        result = processor.process_audio_file(test_file)
        if result:
            print(f"処理済みファイル: {result}")
