#!/usr/bin/env python3
"""
テスト設定ファイル

pytestの設定と共通のフィクスチャを定義します。
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# テスト用の一時ディレクトリ
@pytest.fixture
def temp_dir():
    """一時ディレクトリを作成し、テスト後に削除"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def mock_config():
    """テスト用の設定辞書"""
    return {
        "usb_identifier": "TEST_USB",
        "gdrive_folder_id": "test_folder_id",
        "audio_extensions": [".mp3", ".wav", ".m4a"],
        "max_file_size_mb": 500,
        "parallel_uploads": 3,
        "upload_chunk_size_mb": 10,
        "retry_attempts": 2,
        "retry_delay_seconds": 1,
        "log_level": "DEBUG",
        "exclude_folders": [".Trashes", "System Volume Information"],
        "preserve_folder_structure": True,
        "skip_duplicates": True,
        "use_database": True,
        "notification_enabled": False
    }

@pytest.fixture
def mock_logger():
    """モックロガーを作成"""
    logger = MagicMock()
    logger.log_info = Mock()
    logger.log_error = Mock()
    logger.log_warning = Mock()
    logger.log_success = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    return logger

@pytest.fixture
def sample_audio_files(temp_dir):
    """テスト用のサンプル音声ファイルを作成"""
    files = []
    
    # 異なる拡張子のファイルを作成
    extensions = ['.mp3', '.wav', '.m4a', '.txt', '.pdf']
    for i, ext in enumerate(extensions):
        file_path = Path(temp_dir) / f"test_file_{i}{ext}"
        file_path.write_bytes(b"dummy content" * 100)  # ダミーコンテンツ
        files.append(str(file_path))
    
    # サブディレクトリ内のファイル
    sub_dir = Path(temp_dir) / "subdir"
    sub_dir.mkdir()
    sub_file = sub_dir / "nested.mp3"
    sub_file.write_bytes(b"nested content" * 50)
    files.append(str(sub_file))
    
    return files

@pytest.fixture
def mock_google_drive_service():
    """Google Drive APIのモックサービス"""
    service = MagicMock()
    
    # About API のモック
    about_mock = MagicMock()
    about_mock.get.return_value.execute.return_value = {
        'user': {'emailAddress': 'test@example.com'}
    }
    service.about.return_value = about_mock
    
    # Files API のモック
    files_mock = MagicMock()
    
    # create メソッドのモック
    create_mock = MagicMock()
    create_mock.execute.return_value = {'id': 'test_file_id_123'}
    files_mock.create.return_value = create_mock
    
    # list メソッドのモック
    list_mock = MagicMock()
    list_mock.execute.return_value = {'files': []}
    files_mock.list.return_value = list_mock
    
    # get メソッドのモック
    get_mock = MagicMock()
    get_mock.execute.return_value = {
        'id': 'folder_id_123',
        'name': 'Test Folder',
        'mimeType': 'application/vnd.google-apps.folder',
        'webViewLink': 'https://drive.google.com/drive/folders/test'
    }
    files_mock.get.return_value = get_mock
    
    service.files.return_value = files_mock
    
    return service

@pytest.fixture
def mock_database(temp_dir):
    """テスト用のデータベース"""
    from src.utils.database import SyncDatabase
    
    db_path = Path(temp_dir) / "test_sync.db"
    db = SyncDatabase(str(db_path))
    return db

@pytest.fixture
def usb_mount_path(temp_dir):
    """USBマウントパスのシミュレーション"""
    usb_path = Path(temp_dir) / "Volumes" / "TEST_USB"
    usb_path.mkdir(parents=True)
    
    # サンプル音声ファイルを追加
    audio_files = [
        "song1.mp3",
        "song2.wav",
        "podcast/episode1.m4a",
        "podcast/episode2.mp3"
    ]
    
    for file_path in audio_files:
        full_path = usb_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(b"audio content" * 100)
    
    # 非音声ファイルも追加
    (usb_path / "document.pdf").write_bytes(b"pdf content")
    (usb_path / "image.jpg").write_bytes(b"jpg content")
    
    return str(usb_path)

# pytest設定
def pytest_configure(config):
    """pytest設定のカスタマイズ"""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests"
    )

# カバレッジ除外パターン
def pytest_collection_modifyitems(config, items):
    """テスト実行前の項目修正"""
    # CI環境でのみ統合テストをスキップ
    if os.environ.get('CI'):
        skip_integration = pytest.mark.skip(reason="Skipping integration tests in CI")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
