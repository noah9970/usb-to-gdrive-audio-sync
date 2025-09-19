#!/usr/bin/env python3
"""
File Handler Module
音声ファイルのフィルタリング、検証、パス管理を行う
"""

import os
import hashlib
import json
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import mimetypes

class FileHandler:
    """ファイル処理を管理するクラス"""
    
    def __init__(self, config_path: str = "config/settings.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # 設定値の読み込み
        self.audio_extensions = self.config.get(
            "audio_extensions",
            [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"]
        )
        self.max_file_size_mb = self.config.get("max_file_size_mb", 500)
        self.max_file_size_bytes = self.max_file_size_mb * 1024 * 1024
        self.exclude_folders = self.config.get(
            "exclude_folders",
            [".Spotlight-V100", ".Trashes", "System Volume Information", "$RECYCLE.BIN"]
        )
        self.preserve_folder_structure = self.config.get("preserve_folder_structure", True)
        
        # MIMEタイプの初期化
        mimetypes.init()
    
    def _load_config(self, config_path: str) -> Dict:
        """設定ファイルを読み込む"""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            self.logger.warning(f"Config file not found: {config_path}")
            return {}
    
    def scan_audio_files(self, base_path: str) -> List[Dict[str, any]]:
        """
        指定パスから音声ファイルをスキャン
        
        Args:
            base_path: スキャンするベースパス
            
        Returns:
            音声ファイル情報のリスト
        """
        audio_files = []
        base_path = Path(base_path)
        
        if not base_path.exists():
            self.logger.error(f"Path does not exist: {base_path}")
            return audio_files
        
        self.logger.info(f"Scanning for audio files in: {base_path}")
        
        # ファイルを再帰的に検索
        for root, dirs, files in os.walk(base_path):
            # 除外フォルダをスキップ
            dirs[:] = [d for d in dirs if d not in self.exclude_folders]
            
            for file in files:
                file_path = Path(root) / file
                
                # 音声ファイルかチェック
                if self.is_audio_file(file_path):
                    file_info = self.get_file_info(file_path, base_path)
                    if file_info:
                        audio_files.append(file_info)
                        self.logger.debug(f"Found audio file: {file_path}")
        
        self.logger.info(f"Found {len(audio_files)} audio files")
        return audio_files
    
    def is_audio_file(self, file_path: Path) -> bool:
        """
        ファイルが音声ファイルかどうかを判定
        
        Args:
            file_path: チェックするファイルのパス
            
        Returns:
            音声ファイルの場合True
        """
        # 拡張子チェック
        if file_path.suffix.lower() not in self.audio_extensions:
            return False
        
        # ファイルサイズチェック
        try:
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size_bytes:
                self.logger.warning(
                    f"File too large ({file_size / 1024 / 1024:.2f}MB): {file_path}"
                )
                return False
            
            # 0バイトファイルを除外
            if file_size == 0:
                self.logger.warning(f"Empty file: {file_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking file: {file_path} - {e}")
            return False
        
        return True
    
    def get_file_info(self, file_path: Path, base_path: Path) -> Optional[Dict]:
        """
        ファイルの詳細情報を取得
        
        Args:
            file_path: ファイルのパス
            base_path: ベースパス（相対パス計算用）
            
        Returns:
            ファイル情報の辞書
        """
        try:
            stat = file_path.stat()
            
            # 相対パスを計算
            relative_path = file_path.relative_to(base_path)
            
            # MIMEタイプを推測
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            file_info = {
                "name": file_path.name,
                "path": str(file_path),
                "relative_path": str(relative_path),
                "size": stat.st_size,
                "size_mb": stat.st_size / 1024 / 1024,
                "extension": file_path.suffix.lower(),
                "mime_type": mime_type or "audio/unknown",
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "hash": None  # 後で計算
            }
            
            return file_info
            
        except Exception as e:
            self.logger.error(f"Error getting file info: {file_path} - {e}")
            return None
    
    def calculate_file_hash(self, file_path: str, algorithm: str = "md5") -> str:
        """
        ファイルのハッシュ値を計算
        
        Args:
            file_path: ファイルのパス
            algorithm: ハッシュアルゴリズム（md5, sha1, sha256）
            
        Returns:
            ハッシュ値の文字列
        """
        hash_algorithms = {
            "md5": hashlib.md5,
            "sha1": hashlib.sha1,
            "sha256": hashlib.sha256
        }
        
        if algorithm not in hash_algorithms:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        hasher = hash_algorithms[algorithm]()
        
        try:
            with open(file_path, 'rb') as f:
                # チャンクごとに読み込んでハッシュを計算（メモリ効率）
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Error calculating hash for {file_path}: {e}")
            raise
    
    def get_destination_path(self, source_path: str, base_path: str, destination_root: str) -> str:
        """
        アップロード先のパスを生成
        
        Args:
            source_path: ソースファイルのパス
            base_path: USBメモリのベースパス
            destination_root: アップロード先のルートパス
            
        Returns:
            アップロード先のパス
        """
        source_path = Path(source_path)
        base_path = Path(base_path)
        
        if self.preserve_folder_structure:
            # フォルダ構造を維持
            relative_path = source_path.relative_to(base_path)
            destination_path = Path(destination_root) / relative_path
        else:
            # フラットな構造
            destination_path = Path(destination_root) / source_path.name
        
        return str(destination_path)
    
    def filter_new_files(self, files: List[Dict], existing_hashes: List[str]) -> List[Dict]:
        """
        新規ファイルのみをフィルタリング
        
        Args:
            files: ファイル情報のリスト
            existing_hashes: 既存ファイルのハッシュ値リスト
            
        Returns:
            新規ファイルのリスト
        """
        new_files = []
        existing_hashes_set = set(existing_hashes)
        
        for file_info in files:
            # ハッシュ値を計算
            if not file_info.get("hash"):
                try:
                    file_info["hash"] = self.calculate_file_hash(file_info["path"])
                except Exception as e:
                    self.logger.error(f"Failed to calculate hash: {e}")
                    continue
            
            # 新規ファイルかチェック
            if file_info["hash"] not in existing_hashes_set:
                new_files.append(file_info)
                self.logger.info(f"New file detected: {file_info['name']}")
            else:
                self.logger.debug(f"File already exists: {file_info['name']}")
        
        return new_files
    
    def organize_files_by_type(self, files: List[Dict]) -> Dict[str, List[Dict]]:
        """
        ファイルを拡張子別に整理
        
        Args:
            files: ファイル情報のリスト
            
        Returns:
            拡張子別に整理されたファイルの辞書
        """
        organized = {}
        
        for file_info in files:
            ext = file_info["extension"]
            if ext not in organized:
                organized[ext] = []
            organized[ext].append(file_info)
        
        # 統計情報をログ出力
        for ext, file_list in organized.items():
            total_size = sum(f["size"] for f in file_list) / 1024 / 1024
            self.logger.info(
                f"{ext}: {len(file_list)} files, {total_size:.2f}MB total"
            )
        
        return organized
    
    def validate_file_integrity(self, file_path: str, expected_hash: str) -> bool:
        """
        ファイルの整合性を検証
        
        Args:
            file_path: ファイルのパス
            expected_hash: 期待されるハッシュ値
            
        Returns:
            整合性が確認できた場合True
        """
        try:
            actual_hash = self.calculate_file_hash(file_path)
            is_valid = actual_hash == expected_hash
            
            if not is_valid:
                self.logger.error(
                    f"File integrity check failed: {file_path}\n"
                    f"Expected: {expected_hash}\n"
                    f"Actual: {actual_hash}"
                )
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Error validating file integrity: {e}")
            return False


def main():
    """テスト用のメイン関数"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    handler = FileHandler()
    
    # テスト用のパス（実際のUSBパスに置き換えてテスト）
    test_path = "/Volumes/AUDIO_USB"
    
    if os.path.exists(test_path):
        # 音声ファイルをスキャン
        audio_files = handler.scan_audio_files(test_path)
        
        print(f"\nFound {len(audio_files)} audio files:")
        for file_info in audio_files[:5]:  # 最初の5件を表示
            print(f"- {file_info['name']} ({file_info['size_mb']:.2f}MB)")
        
        # ファイルを拡張子別に整理
        organized = handler.organize_files_by_type(audio_files)
        
        print(f"\nFiles by extension:")
        for ext, files in organized.items():
            print(f"- {ext}: {len(files)} files")
        
        # ハッシュ値の計算テスト
        if audio_files:
            first_file = audio_files[0]
            print(f"\nCalculating hash for: {first_file['name']}")
            file_hash = handler.calculate_file_hash(first_file['path'])
            print(f"MD5: {file_hash}")
    else:
        print(f"Test path not found: {test_path}")
        print("Please connect a USB drive to test.")


if __name__ == "__main__":
    main()
