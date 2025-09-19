#!/usr/bin/env python3
"""
同期履歴データベース管理モジュール

SQLiteを使用して同期履歴を管理し、
重複チェック、差分同期、履歴照会機能を提供します。

主な機能:
- ファイル同期履歴の記録
- ハッシュ値による重複検出
- 同期セッション管理
- 統計情報の集計
- クリーンアップ機能
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from contextlib import contextmanager
import logging

# ローカルモジュール
from utils.logger import Logger


class SyncDatabase:
    """同期履歴データベースクラス"""
    
    def __init__(self, db_path: str = "config/sync_history.db", logger: Optional[Logger] = None):
        """
        初期化
        
        Args:
            db_path: データベースファイルのパス
            logger: ログ管理オブジェクト
        """
        self.db_path = Path(db_path)
        self.logger = logger or logging.getLogger(__name__)
        
        # データベースディレクトリを作成
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # データベースを初期化
        self._init_database()
        
        # 統計情報キャッシュ
        self._stats_cache = None
        self._cache_timestamp = None
    
    def _init_database(self):
        """データベースの初期化とテーブル作成"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 同期セッションテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    usb_path TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    status TEXT DEFAULT 'in_progress',
                    total_files INTEGER DEFAULT 0,
                    synced_files INTEGER DEFAULT 0,
                    failed_files INTEGER DEFAULT 0,
                    skipped_files INTEGER DEFAULT 0,
                    total_size_bytes INTEGER DEFAULT 0,
                    synced_size_bytes INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ファイル同期履歴テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_sync_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    gdrive_file_id TEXT,
                    gdrive_folder_id TEXT,
                    sync_status TEXT NOT NULL,
                    sync_time TIMESTAMP NOT NULL,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sync_sessions (session_id)
                )
            """)
            
            # ファイルハッシュインデックス（重複検出用）
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_hash 
                ON file_sync_history (file_hash)
            """)
            
            # セッションIDインデックス
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON file_sync_history (session_id)
            """)
            
            # 同期時刻インデックス
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_time 
                ON file_sync_history (sync_time)
            """)
            
            # ファイル変更追跡テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    last_modified TIMESTAMP NOT NULL,
                    last_synced TIMESTAMP NOT NULL,
                    gdrive_file_id TEXT,
                    sync_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 設定テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
        self.logger.info("Database initialized successfully")
    
    @contextmanager
    def get_connection(self):
        """データベース接続のコンテキストマネージャー"""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            isolation_level='DEFERRED'
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def create_session(self, usb_path: str) -> str:
        """
        新しい同期セッションを作成
        
        Args:
            usb_path: USBメモリのパス
        
        Returns:
            セッションID
        """
        session_id = self._generate_session_id()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_sessions 
                (session_id, usb_path, start_time, status)
                VALUES (?, ?, ?, ?)
            """, (session_id, usb_path, datetime.now(), 'in_progress'))
            conn.commit()
        
        self.logger.info(f"Created sync session: {session_id}")
        return session_id
    
    def update_session(self, session_id: str, **kwargs):
        """
        セッション情報を更新
        
        Args:
            session_id: セッションID
            **kwargs: 更新するフィールドと値
        """
        allowed_fields = [
            'end_time', 'status', 'total_files', 'synced_files',
            'failed_files', 'skipped_files', 'total_size_bytes',
            'synced_size_bytes', 'error_message'
        ]
        
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)
        
        if not updates:
            return
        
        values.append(session_id)
        query = f"UPDATE sync_sessions SET {', '.join(updates)} WHERE session_id = ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
    
    def complete_session(self, session_id: str, success: bool = True, error: str = None):
        """
        セッションを完了
        
        Args:
            session_id: セッションID
            success: 成功フラグ
            error: エラーメッセージ（失敗時）
        """
        status = 'completed' if success else 'failed'
        self.update_session(
            session_id,
            end_time=datetime.now(),
            status=status,
            error_message=error
        )
        self.logger.info(f"Session {session_id} {status}")
    
    def record_file_sync(self, session_id: str, file_info: Dict) -> int:
        """
        ファイル同期を記録
        
        Args:
            session_id: セッションID
            file_info: ファイル情報の辞書
        
        Returns:
            レコードID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO file_sync_history
                (session_id, file_path, file_name, file_size, file_hash,
                 gdrive_file_id, gdrive_folder_id, sync_status, sync_time,
                 error_message, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                file_info.get('file_path'),
                file_info.get('file_name'),
                file_info.get('file_size', 0),
                file_info.get('file_hash'),
                file_info.get('gdrive_file_id'),
                file_info.get('gdrive_folder_id'),
                file_info.get('sync_status', 'pending'),
                datetime.now(),
                file_info.get('error_message'),
                file_info.get('retry_count', 0)
            ))
            
            # ファイル追跡テーブルも更新
            if file_info.get('sync_status') == 'success':
                self._update_file_tracking(cursor, file_info)
            
            conn.commit()
            return cursor.lastrowid
    
    def _update_file_tracking(self, cursor, file_info: Dict):
        """ファイル追跡情報を更新"""
        cursor.execute("""
            INSERT INTO file_tracking
            (file_path, file_name, file_size, file_hash, last_modified, 
             last_synced, gdrive_file_id, sync_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(file_path) DO UPDATE SET
                file_size = excluded.file_size,
                file_hash = excluded.file_hash,
                last_modified = excluded.last_modified,
                last_synced = excluded.last_synced,
                gdrive_file_id = excluded.gdrive_file_id,
                sync_count = sync_count + 1,
                updated_at = CURRENT_TIMESTAMP
        """, (
            file_info.get('file_path'),
            file_info.get('file_name'),
            file_info.get('file_size'),
            file_info.get('file_hash'),
            file_info.get('last_modified', datetime.now()),
            datetime.now(),
            file_info.get('gdrive_file_id')
        ))
    
    def check_file_exists(self, file_hash: str, gdrive_folder_id: str = None) -> Optional[Dict]:
        """
        ハッシュ値でファイルの存在を確認
        
        Args:
            file_hash: ファイルのハッシュ値
            gdrive_folder_id: Google DriveフォルダID（オプション）
        
        Returns:
            ファイル情報（存在する場合）
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM file_sync_history
                WHERE file_hash = ? AND sync_status = 'success'
            """
            params = [file_hash]
            
            if gdrive_folder_id:
                query += " AND gdrive_folder_id = ?"
                params.append(gdrive_folder_id)
            
            query += " ORDER BY sync_time DESC LIMIT 1"
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def get_files_to_sync(self, usb_path: str, file_list: List[Dict]) -> List[Dict]:
        """
        同期が必要なファイルのリストを取得（差分同期）
        
        Args:
            usb_path: USBメモリのパス
            file_list: スキャンしたファイルリスト
        
        Returns:
            同期が必要なファイルリスト
        """
        files_to_sync = []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for file_info in file_list:
                file_path = file_info['path']
                file_hash = file_info.get('hash')
                
                if not file_hash:
                    # ハッシュがない場合は同期対象
                    files_to_sync.append(file_info)
                    continue
                
                # ファイル追跡テーブルで確認
                cursor.execute("""
                    SELECT * FROM file_tracking
                    WHERE file_path = ? AND file_hash = ?
                """, (file_path, file_hash))
                
                existing = cursor.fetchone()
                
                if not existing:
                    # 新規ファイルまたは変更されたファイル
                    files_to_sync.append(file_info)
                elif file_info.get('force_sync'):
                    # 強制同期フラグがある場合
                    files_to_sync.append(file_info)
        
        self.logger.info(f"Found {len(files_to_sync)} files to sync out of {len(file_list)}")
        return files_to_sync
    
    def get_session_history(self, limit: int = 10) -> List[Dict]:
        """
        最近の同期セッション履歴を取得
        
        Args:
            limit: 取得件数
        
        Returns:
            セッション履歴リスト
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sync_sessions
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_sync_statistics(self) -> Dict:
        """
        同期統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        # キャッシュチェック（5分間有効）
        if self._stats_cache and self._cache_timestamp:
            if datetime.now() - self._cache_timestamp < timedelta(minutes=5):
                return self._stats_cache
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 全体統計
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(*) as total_files_synced,
                    SUM(file_size) as total_bytes_synced,
                    COUNT(DISTINCT file_hash) as unique_files
                FROM file_sync_history
                WHERE sync_status = 'success'
            """)
            overall = dict(cursor.fetchone())
            
            # 今日の統計
            cursor.execute("""
                SELECT 
                    COUNT(*) as files_today,
                    SUM(file_size) as bytes_today
                FROM file_sync_history
                WHERE sync_status = 'success'
                AND DATE(sync_time) = DATE('now')
            """)
            today = dict(cursor.fetchone())
            
            # 最近のエラー
            cursor.execute("""
                SELECT COUNT(*) as recent_errors
                FROM file_sync_history
                WHERE sync_status = 'failed'
                AND sync_time > datetime('now', '-7 days')
            """)
            errors = dict(cursor.fetchone())
            
            # ファイルタイプ別統計
            cursor.execute("""
                SELECT 
                    LOWER(SUBSTR(file_name, -4)) as extension,
                    COUNT(*) as count,
                    SUM(file_size) as total_size
                FROM file_sync_history
                WHERE sync_status = 'success'
                GROUP BY extension
                ORDER BY count DESC
            """)
            by_type = [dict(row) for row in cursor.fetchall()]
            
            stats = {
                'overall': overall,
                'today': today,
                'errors': errors,
                'by_type': by_type,
                'last_updated': datetime.now().isoformat()
            }
            
            # キャッシュ更新
            self._stats_cache = stats
            self._cache_timestamp = datetime.now()
            
            return stats
    
    def cleanup_old_records(self, days: int = 90):
        """
        古いレコードをクリーンアップ
        
        Args:
            days: 保持日数
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 古いセッションを削除
            cursor.execute("""
                DELETE FROM sync_sessions
                WHERE start_time < ?
            """, (cutoff_date,))
            
            sessions_deleted = cursor.rowcount
            
            # 古い同期履歴を削除
            cursor.execute("""
                DELETE FROM file_sync_history
                WHERE sync_time < ?
            """, (cutoff_date,))
            
            files_deleted = cursor.rowcount
            
            # VACUUM実行（データベース最適化）
            cursor.execute("VACUUM")
            
            conn.commit()
            
        self.logger.info(f"Cleanup completed: {sessions_deleted} sessions, {files_deleted} files deleted")
    
    def export_history(self, output_path: str, session_id: str = None):
        """
        履歴をJSON形式でエクスポート
        
        Args:
            output_path: 出力ファイルパス
            session_id: 特定セッションのみエクスポート（オプション）
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if session_id:
                # 特定セッションの履歴
                cursor.execute("""
                    SELECT * FROM file_sync_history
                    WHERE session_id = ?
                    ORDER BY sync_time
                """, (session_id,))
            else:
                # 全履歴
                cursor.execute("""
                    SELECT * FROM file_sync_history
                    ORDER BY sync_time DESC
                    LIMIT 10000
                """)
            
            records = [dict(row) for row in cursor.fetchall()]
            
            # 日時を文字列に変換
            for record in records:
                if record.get('sync_time'):
                    record['sync_time'] = str(record['sync_time'])
                if record.get('created_at'):
                    record['created_at'] = str(record['created_at'])
            
            # JSONファイルに出力
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Exported {len(records)} records to {output_path}")
    
    def _generate_session_id(self) -> str:
        """セッションIDを生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        return f"session_{timestamp}_{random_suffix}"
    
    def get_duplicate_files(self) -> List[Dict]:
        """
        重複ファイルを検出
        
        Returns:
            重複ファイル情報のリスト
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    file_hash,
                    COUNT(*) as duplicate_count,
                    GROUP_CONCAT(file_name) as file_names,
                    SUM(file_size) as total_size
                FROM file_sync_history
                WHERE sync_status = 'success'
                GROUP BY file_hash
                HAVING COUNT(*) > 1
                ORDER BY duplicate_count DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_settings(self, key: str, value: str):
        """
        設定を更新
        
        Args:
            key: 設定キー
            value: 設定値
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, value))
            conn.commit()
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """
        設定を取得
        
        Args:
            key: 設定キー
            default: デフォルト値
        
        Returns:
            設定値
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT value FROM sync_settings
                WHERE key = ?
            """, (key,))
            
            row = cursor.fetchone()
            if row:
                return row['value']
            return default
