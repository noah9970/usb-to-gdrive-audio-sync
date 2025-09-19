#!/usr/bin/env python3
"""
ファイル処理モジュールのユニットテスト
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import hashlib

from src.file_handler import FileHandler


class TestFileHandler:
    """FileHandlerクラスのテスト"""
    
    @pytest.fixture
    def file_handler(self, mock_config):
        """FileHandlerインスタンスを作成"""
        return FileHandler(mock_config)
    
    def test_initialization(self, file_handler, mock_config):
        """初期化のテスト"""
        assert file_handler.config == mock_config
        assert file_handler.audio_extensions == mock_config['audio_extensions']
        assert file_handler.max_file_size == mock_config['max_file_size_mb'] * 1024 * 1024
        assert file_handler.exclude_folders == mock_config['exclude_folders']
    
    def test_is_audio_file(self, file_handler):
        """音声ファイル判定のテスト"""
        # 音声ファイル
        assert file_handler.is_audio_file("song.mp3") == True
        assert file_handler.is_audio_file("music.MP3") == True  # 大文字
        assert file_handler.is_audio_file("audio.wav") == True
        assert file_handler.is_audio_file("track.m4a") == True
        
        # 非音声ファイル
        assert file_handler.is_audio_file("document.pdf") == False
        assert file_handler.is_audio_file("image.jpg") == False
        assert file_handler.is_audio_file("video.mp4") == False
        assert file_handler.is_audio_file("script.py") == False
        assert file_handler.is_audio_file("no_extension") == False
    
    def test_should_exclude_folder(self, file_handler):
        """除外フォルダ判定のテスト"""
        # 除外すべきフォルダ
        assert file_handler.should_exclude_folder(".Trashes") == True
        assert file_handler.should_exclude_folder("System Volume Information") == True
        
        # 除外しないフォルダ
        assert file_handler.should_exclude_folder("Music") == False
        assert file_handler.should_exclude_folder("Audio Files") == False
        assert file_handler.should_exclude_folder("") == False
    
    def test_scan_audio_files(self, file_handler, usb_mount_path):
        """音声ファイルスキャンのテスト"""
        # USBパスから音声ファイルをスキャン
        audio_files = file_handler.scan_audio_files(usb_mount_path)
        
        # 結果を検証
        assert len(audio_files) > 0
        
        # 音声ファイルのみが含まれることを確認
        for file_info in audio_files:
            assert 'path' in file_info
            assert 'name' in file_info
            assert 'size' in file_info
            assert 'relative_path' in file_info
            
            # 拡張子が音声ファイルであることを確認
            file_path = Path(file_info['path'])
            assert file_path.suffix.lower() in file_handler.audio_extensions
            
            # PDFや画像が含まれていないことを確認
            assert not file_info['name'].endswith('.pdf')
            assert not file_info['name'].endswith('.jpg')
    
    def test_scan_audio_files_with_subdirectories(self, file_handler, temp_dir):
        """サブディレクトリを含むスキャンのテスト"""
        # テスト用ディレクトリ構造を作成
        root = Path(temp_dir)
        
        # フォルダ構造を作成
        (root / "Album1").mkdir()
        (root / "Album1" / "track1.mp3").write_bytes(b"audio1")
        (root / "Album1" / "track2.wav").write_bytes(b"audio2")
        
        (root / "Album2").mkdir()
        (root / "Album2" / "song.m4a").write_bytes(b"audio3")
        
        # 除外フォルダ
        (root / ".Trashes").mkdir()
        (root / ".Trashes" / "hidden.mp3").write_bytes(b"hidden")
        
        # スキャン実行
        audio_files = file_handler.scan_audio_files(str(root))
        
        # 結果を検証
        assert len(audio_files) == 3  # 除外フォルダ内のファイルは含まれない
        
        file_names = [f['name'] for f in audio_files]
        assert "track1.mp3" in file_names
        assert "track2.wav" in file_names
        assert "song.m4a" in file_names
        assert "hidden.mp3" not in file_names
    
    def test_file_size_limit(self, file_handler, temp_dir):
        """ファイルサイズ制限のテスト"""
        # 大きなファイルを作成
        large_file = Path(temp_dir) / "large.mp3"
        large_file.write_bytes(b"x" * (file_handler.max_file_size + 1))
        
        # 通常サイズのファイル
        normal_file = Path(temp_dir) / "normal.mp3"
        normal_file.write_bytes(b"x" * 1000)
        
        # スキャン実行
        audio_files = file_handler.scan_audio_files(str(temp_dir))
        
        # 結果を検証
        file_names = [f['name'] for f in audio_files]
        assert "normal.mp3" in file_names
        assert "large.mp3" not in file_names  # サイズ制限で除外される
    
    def test_calculate_hash(self, file_handler, temp_dir):
        """ハッシュ計算のテスト"""
        # テストファイルを作成
        test_file = Path(temp_dir) / "test.mp3"
        test_content = b"test audio content"
        test_file.write_bytes(test_content)
        
        # ハッシュを計算
        calculated_hash = file_handler.calculate_hash(str(test_file))
        
        # 期待されるハッシュ値を計算
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        # 一致することを確認
        assert calculated_hash == expected_hash
