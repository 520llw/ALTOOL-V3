# -*- coding: utf-8 -*-
"""
用户管理模块
负责用户认证、密码加密、权限控制等功能
"""

import logging
import bcrypt
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from .db_manager import DatabaseManager, User, UserLog

# 配置日志
logger = logging.getLogger(__name__)

# 常量配置
MAX_LOGIN_ATTEMPTS = 5  # 最大登录失败次数
LOCKOUT_DURATION = 10  # 锁定时长（分钟）
REMEMBER_ME_DAYS = 7  # 记住我有效期（天）


class UserManager:
    """
    用户管理器
    封装所有用户相关操作：认证、注册、密码管理、权限控制等
    """
    
    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化用户管理器
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager or DatabaseManager()
    
    # ==================== 密码加密相关 ====================
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        使用bcrypt加密密码
        
        Args:
            password: 明文密码
            
        Returns:
            加密后的密码哈希值
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        验证密码是否正确
        
        Args:
            password: 明文密码
            password_hash: 存储的密码哈希值
            
        Returns:
            密码是否匹配
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        验证密码强度
        
        Args:
            password: 密码
            
        Returns:
            (是否合格, 提示信息)
        """
        if len(password) < 6:
            return False, "密码长度至少6位"
        if len(password) > 32:
            return False, "密码长度不能超过32位"
        return True, "密码强度合格"
    
    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """
        清理输入，防止SQL注入
        
        Args:
            input_str: 输入字符串
            
        Returns:
            清理后的字符串
        """
        if not input_str:
            return ""
        # 移除危险字符
        return re.sub(r'[;\'"\\]', '', input_str.strip())
    
    # ==================== 用户认证相关 ====================
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        用户认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            (是否成功, 消息, 用户对象)
        """
        session = self.db.get_session()
        try:
            # 清理输入
            username = self.sanitize_input(username)
            
            # 查找用户
            user = session.query(User).filter_by(username=username).first()
            
            if not user:
                return False, "用户名或密码错误", None
            
            # 检查账号是否被禁用
            if not user.is_active:
                return False, "账号已被禁用，请联系管理员", None
            
            # 检查是否被锁定
            if user.locked_until and user.locked_until > datetime.now():
                remaining = (user.locked_until - datetime.now()).seconds // 60
                return False, f"账号已被锁定，请{remaining + 1}分钟后再试", None
            
            # 验证密码
            if not self.verify_password(password, user.password_hash):
                # 增加失败次数
                user.login_attempts += 1
                
                # 达到最大失败次数，锁定账号
                if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
                    user.locked_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION)
                    session.commit()
                    return False, f"密码错误次数过多，账号已锁定{LOCKOUT_DURATION}分钟", None
                
                session.commit()
                remaining = MAX_LOGIN_ATTEMPTS - user.login_attempts
                return False, f"密码错误，还剩{remaining}次机会", None
            
            # 登录成功，重置失败次数
            user.login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.now()
            session.commit()
            
            # 记录登录日志
            self.add_user_log(user.id, "LOGIN", "用户登录成功")
            
            logger.info(f"用户 {username} 登录成功")
            return True, "登录成功", user
            
        except Exception as e:
            session.rollback()
            logger.error(f"认证失败: {e}")
            return False, "系统错误，请稍后再试", None
        finally:
            session.close()
    
    def logout(self, user_id: int):
        """
        用户登出
        
        Args:
            user_id: 用户ID
        """
        self.add_user_log(user_id, "LOGOUT", "用户登出")
        logger.info(f"用户ID {user_id} 登出")
    
    # ==================== 用户管理相关 ====================
    
    def create_user(self, username: str, password: str, role: str = "user") -> Tuple[bool, str]:
        """
        创建新用户
        
        Args:
            username: 用户名
            password: 密码
            role: 角色 (admin/user)
            
        Returns:
            (是否成功, 消息)
        """
        session = self.db.get_session()
        try:
            # 验证用户名
            username = self.sanitize_input(username)
            if not username or len(username) < 3:
                return False, "用户名至少3个字符"
            if len(username) > 20:
                return False, "用户名不能超过20个字符"
            
            # 检查用户名是否已存在
            existing = session.query(User).filter_by(username=username).first()
            if existing:
                return False, "用户名已存在"
            
            # 验证密码强度
            valid, msg = self.validate_password_strength(password)
            if not valid:
                return False, msg
            
            # 创建用户
            user = User(
                username=username,
                password_hash=self.hash_password(password),
                role=role if role in ['admin', 'user'] else 'user'
            )
            session.add(user)
            session.commit()
            
            logger.info(f"创建用户成功: {username}, 角色: {role}")
            return True, "用户创建成功"
            
        except Exception as e:
            session.rollback()
            logger.error(f"创建用户失败: {e}")
            return False, f"创建失败: {str(e)}"
        finally:
            session.close()
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        修改密码
        
        Args:
            user_id: 用户ID
            old_password: 原密码
            new_password: 新密码
            
        Returns:
            (是否成功, 消息)
        """
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False, "用户不存在"
            
            # 验证原密码
            if not self.verify_password(old_password, user.password_hash):
                return False, "原密码错误"
            
            # 验证新密码强度
            valid, msg = self.validate_password_strength(new_password)
            if not valid:
                return False, msg
            
            # 更新密码
            user.password_hash = self.hash_password(new_password)
            session.commit()
            
            # 记录日志
            self.add_user_log(user_id, "CHANGE_PASSWORD", "修改密码成功")
            
            logger.info(f"用户ID {user_id} 修改密码成功")
            return True, "密码修改成功"
            
        except Exception as e:
            session.rollback()
            logger.error(f"修改密码失败: {e}")
            return False, "修改失败，请稍后再试"
        finally:
            session.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        session = self.db.get_session()
        try:
            return session.query(User).filter_by(id=user_id).first()
        finally:
            session.close()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        session = self.db.get_session()
        try:
            return session.query(User).filter_by(username=username).first()
        finally:
            session.close()

    def get_user_api_key(self, user_id: int) -> Optional[str]:
        """获取用户专属API密钥（为空表示使用系统默认）"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            return user.ai_api_key if user else None
        finally:
            session.close()

    def set_user_api_key(self, user_id: int, api_key: str) -> bool:
        """设置用户专属API密钥（传空串则清除，回退为系统默认）"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False
            user.ai_api_key = api_key if api_key else None
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"设置API密钥失败: {e}")
            return False
        finally:
            session.close()
    
    def get_all_users(self) -> List[User]:
        """获取所有用户"""
        session = self.db.get_session()
        try:
            return session.query(User).order_by(User.created_at.desc()).all()
        finally:
            session.close()
    
    def update_user_status(self, user_id: int, is_active: bool) -> bool:
        """
        更新用户状态（启用/禁用）
        
        Args:
            user_id: 用户ID
            is_active: 是否启用
            
        Returns:
            是否成功
        """
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                user.is_active = is_active
                session.commit()
                action = "ENABLE_USER" if is_active else "DISABLE_USER"
                logger.info(f"用户ID {user_id} 状态更新为: {is_active}")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"更新用户状态失败: {e}")
            return False
        finally:
            session.close()
    
    def update_user_role(self, user_id: int, role: str) -> bool:
        """
        更新用户角色
        
        Args:
            user_id: 用户ID
            role: 新角色
            
        Returns:
            是否成功
        """
        session = self.db.get_session()
        try:
            if role not in ['admin', 'user']:
                return False
            
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                user.role = role
                session.commit()
                logger.info(f"用户ID {user_id} 角色更新为: {role}")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"更新用户角色失败: {e}")
            return False
        finally:
            session.close()
    
    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                session.delete(user)
                session.commit()
                logger.info(f"删除用户ID: {user_id}")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"删除用户失败: {e}")
            return False
        finally:
            session.close()
    
    # ==================== 用户日志相关 ====================
    
    def add_user_log(self, user_id: int, action: str, detail: str = None, 
                     ip_address: str = None) -> bool:
        """
        添加用户操作日志
        
        Args:
            user_id: 用户ID
            action: 操作类型
            detail: 操作详情
            ip_address: IP地址
            
        Returns:
            是否成功
        """
        session = self.db.get_session()
        try:
            log = UserLog(
                user_id=user_id,
                action=action,
                detail=detail,
                ip_address=ip_address
            )
            session.add(log)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"添加用户日志失败: {e}")
            return False
        finally:
            session.close()
    
    def get_user_logs(self, user_id: int = None, action: str = None,
                      start_time: datetime = None, end_time: datetime = None,
                      limit: int = 100) -> List[UserLog]:
        """
        获取用户操作日志
        
        Args:
            user_id: 用户ID（None则获取所有用户日志，需管理员权限）
            action: 操作类型筛选
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            日志列表
        """
        session = self.db.get_session()
        try:
            query = session.query(UserLog)
            
            if user_id:
                query = query.filter_by(user_id=user_id)
            if action:
                query = query.filter_by(action=action)
            if start_time:
                query = query.filter(UserLog.created_at >= start_time)
            if end_time:
                query = query.filter(UserLog.created_at <= end_time)
            
            return query.order_by(UserLog.created_at.desc()).limit(limit).all()
        finally:
            session.close()
    
    def clear_all_logs(self) -> bool:
        """清空所有用户日志（仅管理员）"""
        session = self.db.get_session()
        try:
            session.query(UserLog).delete()
            session.commit()
            logger.info("清空所有用户日志")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"清空日志失败: {e}")
            return False
        finally:
            session.close()
    
    # ==================== 初始化相关 ====================
    
    def init_default_admin(self) -> bool:
        """
        初始化默认管理员账号
        如果不存在admin用户，则创建一个
        
        Returns:
            是否创建了新管理员
        """
        session = self.db.get_session()
        try:
            admin = session.query(User).filter_by(username='admin').first()
            if not admin:
                # 创建默认管理员
                admin = User(
                    username='admin',
                    password_hash=self.hash_password('admin123'),
                    role='admin',
                    is_active=True
                )
                session.add(admin)
                session.commit()
                logger.info("创建默认管理员账号: admin/admin123")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"初始化管理员失败: {e}")
            return False
        finally:
            session.close()
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """获取用户统计信息"""
        session = self.db.get_session()
        try:
            total_users = session.query(User).count()
            active_users = session.query(User).filter_by(is_active=True).count()
            admin_count = session.query(User).filter_by(role='admin').count()
            total_logs = session.query(UserLog).count()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'admin_count': admin_count,
                'total_logs': total_logs
            }
        finally:
            session.close()

