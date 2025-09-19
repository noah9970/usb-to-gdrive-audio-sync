#!/usr/bin/env python3
"""
Google Drive同期モジュール

このモジュールは Google Drive API との連携を担当し、
音声ファイルのアップロード、フォルダ管理、認証処理を行います。

主な機能:
- OAuth 2.0認証
- ファイル・フォルダの作成とアップロード
- 重複チェック
- 並列アップロード処理
- アップロード進捗管理
"""

import os
import json
import mimetypes
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pickle

# Google API クライアントライブラリ
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaInMemoryUpload

# ローカルモジュール
from utils.logger import Logger


class GoogleDriveSync:
    """Google Drive同期クラス"""
    
    # Google Drive API のスコープ
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    # MIMEタイプマッピング
    AUDIO_MIME_TYPES = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.aac': 'audio/aac',
        '.flac': 'audio/flac',
        '.ogg': 'audio/ogg'
    }
    
    def __init__(self, config: Dict, logger: Logger):
        """
        初期化
        
        Args:
            config: 設定辞書
            logger: ログ管理オブジェクト
        """
        self.config = config
        self.logger = logger
        self.service = None
        self.credentials = None
        
        # 設定から値を取得
        self.target_folder_id = config.get('gdrive_folder_id', 'root')
        self.parallel_uploads = config.get('parallel_uploads', 5)
        self.retry_attempts = config.get('retry_attempts', 3)
        self.chunk_size = config.get('upload_chunk_size_mb', 10) * 1024 * 1024
        
        # 認証情報のパス
        self.credentials_path = Path('config/credentials/credentials.json')
        self.token_path = Path('config/credentials/token.pickle')
        
        # アップロード統計
        self.upload_stats = {
            'total_files': 0,
            'uploaded_files': 0,
            'failed_files': 0,
            'total_bytes': 0,
            'uploaded_bytes': 0
        }
        
        # 初期化時に認証を実行
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Google Drive API の認証を行う"""
        try:
            # トークンファイルが存在する場合は読み込み
            if self.token_path.exists():
                with open(self.token_path, 'rb') as token:
                    self.credentials = pickle.load(token)
                self.logger.log_info("既存の認証トークンを読み込みました")
            
            # 認証情報が無効または存在しない場合
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    # トークンをリフレッシュ
                    self.credentials.refresh(Request())
                    self.logger.log_info("認証トークンをリフレッシュしました")
                else:
                    # 新規認証フロー
                    if not self.credentials_path.exists():
                        raise FileNotFoundError(
                            f"認証情報ファイルが見つかりません: {self.credentials_path}\n"
                            "Google Cloud Console から credentials.json をダウンロードし、"
                            f"{self.credentials_path} に配置してください。"
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), 
                        self.SCOPES
                    )
                    self.credentials = flow.run_local_server(port=0)
                    self.logger.log_info("新規認証が完了しました")
                
                # トークンを保存
                self.token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.credentials, token)
            
            # Google Drive サービスを構築
            self.service = build('drive', 'v3', credentials=self.credentials)
            self.logger.log_success("Google Drive API への接続が確立されました")
            
        except Exception as e:
            self.logger.log_error(f"認証エラー: {e}")
            raise
    
    def check_connection(self) -> bool:
        """
        Google Drive への接続を確認
        
        Returns:
            接続成功時True
        """
        try:
            # About API を使用して接続テスト
            about = self.service.about().get(fields="user").execute()
            user_info = about.get('user', {})
            email = user_info.get('emailAddress', 'Unknown')
            self.logger.log_info(f"接続確認成功: {email}")
            return True
        except Exception as e:
            self.logger.log_error(f"接続確認失敗: {e}")
            return False
    
    def create_folder(self, folder_name: str, parent_id: str = None) -> str:
        """
        Google Drive にフォルダを作成
        
        Args:
            folder_name: フォルダ名
            parent_id: 親フォルダのID（省略時はルート）
        
        Returns:
            作成したフォルダのID
        """
        if parent_id is None:
            parent_id = self.target_folder_id
        
        try:
            # 既存フォルダをチェック
            existing = self._find_folder(folder_name, parent_id)
            if existing:
                self.logger.log_info(f"フォルダは既に存在します: {folder_name}")
                return existing
            
            # フォルダメタデータ
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            
            # フォルダ作成
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            self.logger.log_success(f"フォルダを作成しました: {folder_name} (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            self.logger.log_error(f"フォルダ作成エラー: {e}")
            raise
    
    def _find_folder(self, folder_name: str, parent_id: str) -> Optional[str]:
        """
        指定された名前のフォルダを検索
        
        Args:
            folder_name: フォルダ名
            parent_id: 親フォルダのID
        
        Returns:
            フォルダが見つかった場合そのID、見つからない場合None
        """
        try:
            query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = response.get('files', [])
            if files:
                return files[0]['id']
            return None
            
        except Exception as e:
            self.logger.log_error(f"フォルダ検索エラー: {e}")
            return None
    
    def check_file_exists(self, file_name: str, parent_id: str = None, file_hash: str = None) -> bool:
        """
        ファイルの存在確認
        
        Args:
            file_name: ファイル名
            parent_id: 親フォルダのID
            file_hash: ファイルのハッシュ値（オプション）
        
        Returns:
            ファイルが存在する場合True
        """
        if parent_id is None:
            parent_id = self.target_folder_id
        
        try:
            # ファイル名で検索
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, md5Checksum)'
            ).execute()
            
            files = response.get('files', [])
            
            if not files:
                return False
            
            # ハッシュ値でも確認（提供されている場合）
            if file_hash:
                for file in files:
                    if file.get('md5Checksum') == file_hash:
                        return True
                return False
            
            return True
            
        except Exception as e:
            self.logger.log_error(f"ファイル存在確認エラー: {e}")
            return False
    
    def upload_file(self, local_path: str, parent_id: str = None, 
                   preserve_path: bool = True) -> Optional[str]:
        """
        ファイルをGoogle Driveにアップロード
        
        Args:
            local_path: ローカルファイルパス
            parent_id: 親フォルダのID
            preserve_path: ディレクトリ構造を保持するか
        
        Returns:
            アップロードしたファイルのID、失敗時はNone
        """
        if parent_id is None:
            parent_id = self.target_folder_id
        
        local_path = Path(local_path)
        
        try:
            # ファイルサイズチェック
            file_size = local_path.stat().st_size
            max_size = self.config.get('max_file_size_mb', 500) * 1024 * 1024
            
            if file_size > max_size:
                self.logger.log_warning(f"ファイルサイズが上限を超えています: {local_path.name}")
                return None
            
            # MIMEタイプの判定
            mime_type = self.AUDIO_MIME_TYPES.get(
                local_path.suffix.lower(),
                mimetypes.guess_type(str(local_path))[0] or 'application/octet-stream'
            )
            
            # ディレクトリ構造の処理
            upload_parent_id = parent_id
            if preserve_path and local_path.parent.name:
                # 親ディレクトリ構造を再現
                folders = []
                current = local_path.parent
                while current.name:
                    folders.append(current.name)
                    current = current.parent
                
                # フォルダを逆順で作成
                for folder_name in reversed(folders):
                    upload_parent_id = self.create_folder(folder_name, upload_parent_id)
            
            # 重複チェック
            if self.check_file_exists(local_path.name, upload_parent_id):
                self.logger.log_info(f"ファイルは既に存在します（スキップ）: {local_path.name}")
                return None
            
            # ファイルメタデータ
            file_metadata = {
                'name': local_path.name,
                'parents': [upload_parent_id]
            }
            
            # メディアアップロード（チャンク分割対応）
            media = MediaFileUpload(
                str(local_path),
                mimetype=mime_type,
                resumable=True,
                chunksize=self.chunk_size
            )
            
            # アップロード実行
            self.logger.log_info(f"アップロード開始: {local_path.name} ({file_size / 1024 / 1024:.1f} MB)")
            
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )
            
            # プログレス表示付きアップロード
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    if progress % 20 == 0:  # 20%ごとに進捗表示
                        self.logger.log_info(f"  {local_path.name}: {progress}% 完了")
            
            file_id = response.get('id')
            self.logger.log_success(f"アップロード完了: {local_path.name} (ID: {file_id})")
            
            # 統計更新
            self.upload_stats['uploaded_files'] += 1
            self.upload_stats['uploaded_bytes'] += file_size
            
            return file_id
            
        except Exception as e:
            self.logger.log_error(f"アップロードエラー ({local_path.name}): {e}")
            self.upload_stats['failed_files'] += 1
            
            # リトライロジック
            for attempt in range(1, self.retry_attempts):
                try:
                    self.logger.log_info(f"リトライ {attempt}/{self.retry_attempts}: {local_path.name}")
                    return self.upload_file(local_path, parent_id, preserve_path)
                except:
                    continue
            
            return None
    
    def upload_files_parallel(self, file_paths: List[str], parent_id: str = None) -> Dict[str, str]:
        """
        複数ファイルを並列でアップロード
        
        Args:
            file_paths: アップロードするファイルパスのリスト
            parent_id: 親フォルダのID
        
        Returns:
            {ファイルパス: ファイルID}の辞書
        """
        if parent_id is None:
            parent_id = self.target_folder_id
        
        results = {}
        
        # 統計リセット
        self.upload_stats['total_files'] = len(file_paths)
        self.upload_stats['total_bytes'] = sum(Path(p).stat().st_size for p in file_paths)
        
        self.logger.log_info(f"並列アップロード開始: {len(file_paths)} ファイル")
        
        with ThreadPoolExecutor(max_workers=self.parallel_uploads) as executor:
            # ジョブを投入
            future_to_path = {
                executor.submit(self.upload_file, path, parent_id): path
                for path in file_paths
            }
            
            # 完了を待機
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    file_id = future.result()
                    if file_id:
                        results[path] = file_id
                except Exception as e:
                    self.logger.log_error(f"並列アップロードエラー ({path}): {e}")
        
        # 統計表示
        self._print_upload_summary()
        
        return results
    
    def _print_upload_summary(self) -> None:
        """アップロード統計サマリーを表示"""
        stats = self.upload_stats
        success_rate = (stats['uploaded_files'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
        uploaded_mb = stats['uploaded_bytes'] / 1024 / 1024
        total_mb = stats['total_bytes'] / 1024 / 1024
        
        summary = f"""
        ====== アップロードサマリー ======
        総ファイル数: {stats['total_files']}
        成功: {stats['uploaded_files']}
        失敗: {stats['failed_files']}
        成功率: {success_rate:.1f}%
        アップロード容量: {uploaded_mb:.1f} / {total_mb:.1f} MB
        ================================
        """
        
        self.logger.log_success(summary)
    
    def create_sync_folder_structure(self) -> str:
        """
        同期用のフォルダ構造を作成
        
        Returns:
            本日の同期フォルダID
        """
        try:
            # 年フォルダを作成
            year_folder = self.create_folder(
                f"{datetime.now().year}年",
                self.target_folder_id
            )
            
            # 月フォルダを作成
            month_folder = self.create_folder(
                f"{datetime.now().month:02d}月",
                year_folder
            )
            
            # 日付フォルダを作成
            date_str = datetime.now().strftime("%Y%m%d")
            date_folder = self.create_folder(
                f"sync_{date_str}",
                month_folder
            )
            
            return date_folder
            
        except Exception as e:
            self.logger.log_error(f"フォルダ構造作成エラー: {e}")
            raise
    
    def get_folder_info(self, folder_id: str = None) -> Dict:
        """
        フォルダ情報を取得
        
        Args:
            folder_id: フォルダID（省略時はターゲットフォルダ）
        
        Returns:
            フォルダ情報の辞書
        """
        if folder_id is None:
            folder_id = self.target_folder_id
        
        try:
            folder = self.service.files().get(
                fileId=folder_id,
                fields='id, name, mimeType, webViewLink'
            ).execute()
            
            return folder
            
        except Exception as e:
            self.logger.log_error(f"フォルダ情報取得エラー: {e}")
            return {}
