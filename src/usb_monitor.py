#!/usr/bin/env python3
"""
USB Monitor Module
USBメモリの接続・切断を監視し、特定のUSBメモリを検出する
"""

import os
import time
import subprocess
import json
import logging
from typing import Dict, List, Optional, Callable
from pathlib import Path
import plistlib
import threading

# macOS固有のインポート
try:
    from Foundation import NSObject, NSNotificationCenter, NSWorkspace
    from AppKit import NSWorkspaceDidMountNotification, NSWorkspaceDidUnmountNotification
    MACOS_AVAILABLE = True
except ImportError:
    MACOS_AVAILABLE = False
    print("Warning: macOS frameworks not available. Using fallback method.")

class USBMonitor:
    """USBメモリの監視と検出を行うクラス"""
    
    def __init__(self, config_path: str = "config/settings.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self.usb_identifier = self.config.get("usb_identifier", "AUDIO_USB")
        self.mount_callback = None
        self.unmount_callback = None
        self.is_monitoring = False
        self.monitor_thread = None
        
        # macOS通知センター用のオブザーバー
        if MACOS_AVAILABLE:
            self.observer = VolumeObserver.alloc().init()
            self.observer.monitor = self
    
    def _load_config(self, config_path: str) -> Dict:
        """設定ファイルを読み込む"""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            self.logger.warning(f"Config file not found: {config_path}")
            return {}
    
    def get_mounted_volumes(self) -> List[Dict[str, str]]:
        """
        現在マウントされているボリュームのリストを取得
        
        Returns:
            ボリューム情報のリスト
        """
        volumes = []
        
        try:
            # diskutilコマンドで情報取得
            result = subprocess.run(
                ['diskutil', 'list', '-plist'],
                capture_output=True,
                text=False
            )
            
            if result.returncode == 0:
                plist_data = plistlib.loads(result.stdout)
                
                # 各ディスクをチェック
                for disk in plist_data.get('AllDisksAndPartitions', []):
                    # パーティションをチェック
                    for partition in disk.get('Partitions', []):
                        volume_name = partition.get('VolumeName')
                        mount_point = partition.get('MountPoint')
                        
                        if volume_name and mount_point:
                            volume_info = {
                                'name': volume_name,
                                'path': mount_point,
                                'device': partition.get('DeviceIdentifier', ''),
                                'size': partition.get('Size', 0),
                                'type': partition.get('Content', '')
                            }
                            volumes.append(volume_info)
                            self.logger.debug(f"Found volume: {volume_info}")
            
        except Exception as e:
            self.logger.error(f"Error getting mounted volumes: {e}")
        
        return volumes
    
    def is_target_usb(self, volume_path: str) -> bool:
        """
        指定されたボリュームが監視対象のUSBメモリかどうかを判定
        
        Args:
            volume_path: ボリュームのマウントパス
            
        Returns:
            対象のUSBメモリの場合True
        """
        try:
            volume_name = os.path.basename(volume_path)
            
            # ボリューム名で判定
            if self.usb_identifier in volume_name:
                self.logger.info(f"Target USB detected: {volume_name}")
                return True
            
            # .volumeIDファイルで判定（カスタム識別子）
            volume_id_file = os.path.join(volume_path, '.volumeID')
            if os.path.exists(volume_id_file):
                with open(volume_id_file, 'r') as f:
                    volume_id = f.read().strip()
                    if volume_id == self.usb_identifier:
                        self.logger.info(f"Target USB detected by ID: {volume_name}")
                        return True
            
        except Exception as e:
            self.logger.error(f"Error checking USB: {e}")
        
        return False
    
    def on_mount(self, mount_callback: Callable[[str], None]):
        """
        USBマウント時のコールバックを設定
        
        Args:
            mount_callback: マウント時に呼ばれる関数（パスを引数に取る）
        """
        self.mount_callback = mount_callback
    
    def on_unmount(self, unmount_callback: Callable[[str], None]):
        """
        USBアンマウント時のコールバックを設定
        
        Args:
            unmount_callback: アンマウント時に呼ばれる関数（パスを引数に取る）
        """
        self.unmount_callback = unmount_callback
    
    def _handle_mount(self, volume_path: str):
        """マウントイベントを処理"""
        if self.is_target_usb(volume_path):
            self.logger.info(f"Target USB mounted: {volume_path}")
            if self.mount_callback:
                self.mount_callback(volume_path)
    
    def _handle_unmount(self, volume_path: str):
        """アンマウントイベントを処理"""
        self.logger.info(f"Volume unmounted: {volume_path}")
        if self.unmount_callback:
            self.unmount_callback(volume_path)
    
    def start_monitoring(self):
        """USBの監視を開始"""
        if self.is_monitoring:
            self.logger.warning("Already monitoring")
            return
        
        self.is_monitoring = True
        
        if MACOS_AVAILABLE:
            self._start_macos_monitoring()
        else:
            self._start_fallback_monitoring()
        
        self.logger.info("USB monitoring started")
    
    def _start_macos_monitoring(self):
        """macOS固有の監視方法を使用"""
        workspace = NSWorkspace.sharedWorkspace()
        notification_center = workspace.notificationCenter()
        
        # マウント通知の登録
        notification_center.addObserver_selector_name_object_(
            self.observer,
            'volumeDidMount:',
            NSWorkspaceDidMountNotification,
            None
        )
        
        # アンマウント通知の登録
        notification_center.addObserver_selector_name_object_(
            self.observer,
            'volumeDidUnmount:',
            NSWorkspaceDidUnmountNotification,
            None
        )
    
    def _start_fallback_monitoring(self):
        """フォールバック監視方法（ポーリング）"""
        def monitor_loop():
            known_volumes = set()
            
            # 初期状態を取得
            for volume in self.get_mounted_volumes():
                known_volumes.add(volume['path'])
            
            while self.is_monitoring:
                current_volumes = set()
                
                for volume in self.get_mounted_volumes():
                    current_volumes.add(volume['path'])
                    
                    # 新しくマウントされたボリューム
                    if volume['path'] not in known_volumes:
                        self._handle_mount(volume['path'])
                
                # アンマウントされたボリューム
                for path in known_volumes - current_volumes:
                    self._handle_unmount(path)
                
                known_volumes = current_volumes
                time.sleep(2)  # 2秒ごとにチェック
        
        self.monitor_thread = threading.Thread(target=monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """USBの監視を停止"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        if MACOS_AVAILABLE:
            workspace = NSWorkspace.sharedWorkspace()
            notification_center = workspace.notificationCenter()
            notification_center.removeObserver_(self.observer)
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("USB monitoring stopped")
    
    def check_current_usb(self) -> Optional[str]:
        """
        現在接続されている対象USBをチェック
        
        Returns:
            対象USBのパス、なければNone
        """
        volumes = self.get_mounted_volumes()
        
        for volume in volumes:
            if self.is_target_usb(volume['path']):
                return volume['path']
        
        return None


if MACOS_AVAILABLE:
    class VolumeObserver(NSObject):
        """macOS通知を受け取るためのオブザーバークラス"""
        
        monitor = None
        
        def volumeDidMount_(self, notification):
            """ボリュームがマウントされた時の処理"""
            info = notification.userInfo()
            if info:
                volume_path = info.get('NSDevicePath')
                if volume_path and self.monitor:
                    self.monitor._handle_mount(str(volume_path))
        
        def volumeDidUnmount_(self, notification):
            """ボリュームがアンマウントされた時の処理"""
            info = notification.userInfo()
            if info:
                volume_path = info.get('NSDevicePath')
                if volume_path and self.monitor:
                    self.monitor._handle_unmount(str(volume_path))


def main():
    """テスト用のメイン関数"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    monitor = USBMonitor()
    
    # コールバック関数の定義
    def on_usb_mounted(path):
        print(f"✅ Target USB mounted at: {path}")
        print("Starting sync process...")
    
    def on_usb_unmounted(path):
        print(f"❌ USB unmounted: {path}")
    
    # コールバックを設定
    monitor.on_mount(on_usb_mounted)
    monitor.on_unmount(on_usb_unmounted)
    
    # 現在接続されているUSBをチェック
    current_usb = monitor.check_current_usb()
    if current_usb:
        print(f"Target USB already connected: {current_usb}")
    
    # 監視を開始
    print("Starting USB monitoring... (Press Ctrl+C to stop)")
    monitor.start_monitoring()
    
    try:
        # 監視を継続
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping USB monitoring...")
        monitor.stop_monitoring()
        print("Done.")


if __name__ == "__main__":
    main()
