#!/usr/bin/env python3
"""
データベース管理モジュールのユニットテスト
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import json

from src.utils.database import SyncDatabase


class TestSyncDatabase:
    """SyncDatabaseクラスのテスト"""
    
    @pytest.fixture
    def db(self, temp_dir):
        """テスト用データベースインスタンス"""
        db_path = Path(temp_dir) / "test.db"
        return SyncDatabase(str(db_path))
    
    def test_initialization(self, db, temp_dir):
        """データベース初期化のテスト"""
        # データベースファイルが作成されていることを確認
        db_file = Path(temp_dir) / "test.db"
        assert db_file.exists()
        
        # テーブルが作成されていることを確認
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # sync_sessionsテーブル
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_sessions'")
            assert cursor.fetchone() is not None
            
            # file_sync_historyテーブル
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_sync_history'")
            assert cursor.fetchone() is not None
            
            # file_trackingテーブル
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_tracking'")
            assert cursor.fetchone() is not None
            
            # sync_settingsテーブル
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_settings'")
            assert cursor.fetchone() is not None
    
    def test_create_session(self, db):
        """セッション作成のテスト"""
        # セッションを作成
        usb_path = "/Volumes/TEST_USB"
        session_id = db.create_session(usb_path)
        
        # セッションIDが返されることを確認
        assert session_id is not None
        assert session_id.startswith("session_")
        
        # データベースに記録されていることを確認
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sync_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            
            assert row is not None
            assert row['usb_path'] == usb_path
            assert row['status'] == 'in_progress'
    
    def test_update_session(self, db):
        """セッション更新のテスト"""
        # セッションを作成
        session_id = db.create_session("/test/path")
        
        # セッションを更新
        db.update_session(
            session_id,
            total_files=10,
            synced_files=8,
            failed_files=2,
            total_size_bytes=1000000
        )
        
        # 更新が反映されていることを確認
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sync_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            
            assert row['total_files'] == 10
            assert row['synced_files'] == 8
            assert row['failed_files'] == 2
            assert row['total_size_bytes'] == 1000000
    
    def test_complete_session(self, db):
        """セッション完了のテスト"""
        # セッションを作成
        session_id = db.create_session("/test/path")
        
        # セッションを完了（成功）
        db.complete_session(session_id, success=True)
        
        # ステータスが更新されていることを確認
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sync_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            
            assert row['status'] == 'completed'
            assert row['end_time'] is not None
        
        # セッションを作成（失敗ケース）
        session_id2 = db.create_session("/test/path2")
        db.complete_session(session_id2, success=False, error="Test error")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sync_sessions WHERE session_id = ?", (session_id2,))
            row = cursor.fetchone()
            
            assert row['status'] == 'failed'
            assert row['error_message'] == "Test error"
    
    def test_record_file_sync(self, db):
        """ファイル同期記録のテスト"""
        # セッションを作成
        session_id = db.create_session("/test/path")
        
        # ファイル同期を記録
        file_info = {
            'file_path': '/test/audio.mp3',
            'file_name': 'audio.mp3',
            'file_size': 5000000,
            'file_hash': 'abc123def456',
            'gdrive_file_id': 'gdrive_123',
            'gdrive_folder_id': 'folder_123',
            'sync_status': 'success',
            'error_message': None,
            'retry_count': 0
        }
        
        record_id = db.record_file_sync(session_id, file_info)
        
        # レコードが作成されていることを確認
        assert record_id is not None
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_sync_history WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            
            assert row is not None
            assert row['file_name'] == 'audio.mp3'
            assert row['file_size'] == 5000000
            assert row['file_hash'] == 'abc123def456'
            assert row['sync_status'] == 'success'
    
    def test_check_file_exists(self, db):
        """ファイル存在確認のテスト"""
        # セッションとファイル同期を記録
        session_id = db.create_session("/test/path")
        
        file_info = {
            'file_path': '/test/exists.mp3',
            'file_name': 'exists.mp3',
            'file_size': 1000,
            'file_hash': 'hash123',
            'gdrive_folder_id': 'folder_abc',
            'sync_status': 'success'
        }
        
        db.record_file_sync(session_id, file_info)
        
        # ファイルが存在することを確認
        result = db.check_file_exists('hash123', 'folder_abc')
        assert result is not None
        assert result['file_hash'] == 'hash123'
        
        # 存在しないファイルを確認
        result = db.check_file_exists('nonexistent_hash', 'folder_abc')
        assert result is None
        
        # 異なるフォルダでの確認
        result = db.check_file_exists('hash123', 'different_folder')
        assert result is None
    
    def test_get_files_to_sync(self, db):
        """同期対象ファイル取得のテスト"""
        # ファイル追跡情報を追加
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO file_tracking 
                (file_path, file_name, file_size, file_hash, last_modified, last_synced)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                '/test/existing.mp3', 'existing.mp3', 1000, 'hash_existing',
                datetime.now(), datetime.now()
            ))
            conn.commit()
        
        # テストファイルリスト
        file_list = [
            # 既存ファイル（同期不要）
            {
                'path': '/test/existing.mp3',
                'hash': 'hash_existing',
                'name': 'existing.mp3',
                'size': 1000
            },
            # 新規ファイル（同期必要）
            {
                'path': '/test/new.mp3',
                'hash': 'hash_new',
                'name': 'new.mp3',
                'size': 2000
            },
            # 変更されたファイル（同期必要）
            {
                'path': '/test/existing.mp3',
                'hash': 'hash_changed',
                'name': 'existing.mp3',
                'size': 1500
            }
        ]
        
        # 同期対象を取得
        files_to_sync = db.get_files_to_sync("/test", file_list)
        
        # 新規ファイルと変更ファイルが含まれることを確認
        assert len(files_to_sync) >= 1
        sync_paths = [f['path'] for f in files_to_sync]
        assert '/test/new.mp3' in sync_paths
    
    def test_get_sync_statistics(self, db):
        """統計情報取得のテスト"""
        # テストデータを作成
        session_id = db.create_session("/test/path")
        
        for i in range(5):
            file_info = {
                'file_path': f'/test/file{i}.mp3',
                'file_name': f'file{i}.mp3',
                'file_size': 1000 * (i + 1),
                'file_hash': f'hash{i}',
                'sync_status': 'success' if i < 4 else 'failed'
            }
            db.record_file_sync(session_id, file_info)
        
        # 統計情報を取得
        stats = db.get_sync_statistics()
        
        # 統計情報が含まれることを確認
        assert 'overall' in stats
        assert 'today' in stats
        assert 'errors' in stats
        assert 'by_type' in stats
        
        # キャッシュが機能することを確認
        stats2 = db.get_sync_statistics()
        assert stats == stats2  # キャッシュから同じデータが返される
    
    def test_cleanup_old_records(self, db):
        """古いレコードのクリーンアップテスト"""
        # 古いセッションを作成
        old_date = datetime.now() - timedelta(days=100)
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_sessions 
                (session_id, usb_path, start_time, status)
                VALUES (?, ?, ?, ?)
            """, ('old_session', '/old/path', old_date, 'completed'))
            conn.commit()
        
        # 新しいセッションも作成
        recent_session = db.create_session("/recent/path")
        
        # クリーンアップ実行
        db.cleanup_old_records(days=90)
        
        # 古いセッションが削除されていることを確認
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sync_sessions WHERE session_id = 'old_session'")
            assert cursor.fetchone() is None
            
            # 新しいセッションは残っていることを確認
            cursor.execute("SELECT * FROM sync_sessions WHERE session_id = ?", (recent_session,))
            assert cursor.fetchone() is not None
    
    def test_export_history(self, db, temp_dir):
        """履歴エクスポートのテスト"""
        # テストデータを作成
        session_id = db.create_session("/test/path")
        
        for i in range(3):
            file_info = {
                'file_path': f'/test/file{i}.mp3',
                'file_name': f'file{i}.mp3',
                'file_size': 1000,
                'file_hash': f'hash{i}',
                'sync_status': 'success'
            }
            db.record_file_sync(session_id, file_info)
        
        # エクスポート実行
        export_path = Path(temp_dir) / "export.json"
        db.export_history(str(export_path), session_id)
        
        # エクスポートファイルが作成されていることを確認
        assert export_path.exists()
        
        # 内容を確認
        with open(export_path, 'r') as f:
            exported_data = json.load(f)
        
        assert len(exported_data) == 3
        assert all('file_name' in record for record in exported_data)
        assert all('sync_status' in record for record in exported_data)
    
    def test_settings_management(self, db):
        """設定管理のテスト"""
        # 設定を保存
        db.update_settings('test_key', 'test_value')
        
        # 設定を取得
        value = db.get_setting('test_key')
        assert value == 'test_value'
        
        # 存在しない設定を取得
        value = db.get_setting('nonexistent', 'default')
        assert value == 'default'
        
        # 設定を更新
        db.update_settings('test_key', 'updated_value')
        value = db.get_setting('test_key')
        assert value == 'updated_value'
    
    def test_get_duplicate_files(self, db):
        """重複ファイル検出のテスト"""
        # セッションを作成
        session_id = db.create_session("/test/path")
        
        # 同じハッシュを持つファイルを複数記録
        for i in range(3):
            file_info = {
                'file_path': f'/test/copy{i}.mp3',
                'file_name': f'copy{i}.mp3',
                'file_size': 1000,
                'file_hash': 'duplicate_hash',
                'sync_status': 'success'
            }
            db.record_file_sync(session_id, file_info)
        
        # ユニークなファイルも追加
        file_info = {
            'file_path': '/test/unique.mp3',
            'file_name': 'unique.mp3',
            'file_size': 2000,
            'file_hash': 'unique_hash',
            'sync_status': 'success'
        }
        db.record_file_sync(session_id, file_info)
        
        # 重複を検出
        duplicates = db.get_duplicate_files()
        
        # 重複が検出されることを確認
        assert len(duplicates) > 0
        
        # duplicate_hashが含まれることを確認
        duplicate_hashes = [d['file_hash'] for d in duplicates]
        assert 'duplicate_hash' in duplicate_hashes
        
        # 重複数が正しいことを確認
        for dup in duplicates:
            if dup['file_hash'] == 'duplicate_hash':
                assert dup['duplicate_count'] == 3
