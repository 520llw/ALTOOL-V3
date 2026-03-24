# -*- coding: utf-8 -*-
"""
数据库管理模块
使用SQLAlchemy ORM封装CRUD操作
"""

import re
import logging
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool

from .config import DATABASE_PATH

# 配置日志
logger = logging.getLogger(__name__)

# 创建基类
Base = declarative_base()


class StandardParam(Base):
    """
    标准化参数表
    存储所有标准参数名称、单位和器件类型
    """
    __tablename__ = 'standard_params'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    param_name = Column(String(100), unique=True, nullable=False, comment='标准参数名')
    param_name_en = Column(String(200), comment='英文参数名/描述')
    param_type = Column(String(100), comment='器件类型(Si MOSFET/SiC MOSFET/IGBT,逗号分隔)')
    unit = Column(String(50), comment='参数单位')
    category = Column(String(50), comment='参数分类(基本信息/电压/电流/电阻/电容/电荷/时间/热特性/其他)')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 关联变体
    variants = relationship("ParamVariant", back_populates="standard_param", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<StandardParam(id={self.id}, name='{self.param_name}')>"


class ParamVariant(Base):
    """
    参数变体表
    存储同一参数在不同厂家的不同命名方式
    """
    __tablename__ = 'param_variants'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    param_id = Column(Integer, ForeignKey('standard_params.id', ondelete='CASCADE'), nullable=False)
    variant_name = Column(String(200), nullable=False, comment='变体名称')
    vendor = Column(String(100), comment='对应厂家')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    
    # 关联标准参数
    standard_param = relationship("StandardParam", back_populates="variants")
    
    def __repr__(self):
        return f"<ParamVariant(id={self.id}, name='{self.variant_name}')>"


class ParseResult(Base):
    """
    解析结果表
    存储PDF解析的结果数据（按用户隔离）
    """
    __tablename__ = 'parse_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, comment='关联用户ID')
    pdf_name = Column(String(500), nullable=False, comment='PDF文件名')
    pdf_path = Column(String(1000), comment='PDF文件路径')
    device_type = Column(String(50), comment='器件类型')
    manufacturer = Column(String(100), comment='厂家')
    opn = Column(String(100), comment='器件型号')
    param_id = Column(Integer, ForeignKey('standard_params.id'), comment='关联标准参数ID')
    param_name = Column(String(100), comment='参数名')
    param_value = Column(String(200), comment='参数值')
    test_condition = Column(Text, comment='测试条件')
    parse_time = Column(DateTime, default=datetime.now, comment='解析时间')
    is_success = Column(Boolean, default=True, comment='是否提取成功')
    error_message = Column(Text, comment='错误信息')
    
    def __repr__(self):
        return f"<ParseResult(id={self.id}, user_id={self.user_id}, pdf='{self.pdf_name}', param='{self.param_name}')>"


class ParseLog(Base):
    """
    解析日志表
    记录解析过程中的日志信息
    """
    __tablename__ = 'parse_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pdf_name = Column(String(500), comment='PDF文件名')
    log_type = Column(String(20), comment='日志类型(INFO/WARNING/ERROR/SUCCESS)')
    content = Column(Text, comment='日志内容')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    
    def __repr__(self):
        return f"<ParseLog(id={self.id}, type='{self.log_type}')>"


class User(Base):
    """
    用户表
    存储系统用户信息
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment='用户名')
    password_hash = Column(String(128), nullable=False, comment='密码哈希值(bcrypt)')
    role = Column(String(20), default='user', comment='角色(admin/user)')
    is_active = Column(Boolean, default=True, comment='是否启用')
    login_attempts = Column(Integer, default=0, comment='登录失败次数')
    locked_until = Column(DateTime, comment='锁定截止时间')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    last_login = Column(DateTime, comment='最后登录时间')
    ai_api_key = Column(String(256), nullable=True, comment='用户专属API密钥（为空则使用系统默认）')
    
    # 关联操作日志
    logs = relationship("UserLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class UserLog(Base):
    """
    用户操作日志表
    记录用户的所有操作行为
    """
    __tablename__ = 'user_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    action = Column(String(100), nullable=False, comment='操作类型(LOGIN/LOGOUT/PARSE/EXPORT等)')
    detail = Column(Text, comment='操作详情')
    ip_address = Column(String(50), comment='IP地址')
    created_at = Column(DateTime, default=datetime.now, comment='操作时间')
    
    # 关联用户
    user = relationship("User", back_populates="logs")
    
    def __repr__(self):
        return f"<UserLog(id={self.id}, user_id={self.user_id}, action='{self.action}')>"


class TableRecord(Base):
    """
    生成表格记录表
    存储按条件生成的Excel表格记录
    """
    __tablename__ = 'table_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(200), nullable=False, comment='表格文件名')
    device_type = Column(String(50), nullable=False, comment='器件类型')
    pdf_count = Column(Integer, default=0, comment='包含的PDF文件数量')
    pdf_list = Column(Text, comment='PDF文件列表(JSON格式)')
    file_path = Column(String(500), nullable=False, comment='表格文件路径')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    created_by = Column(String(50), comment='创建用户')
    
    def __repr__(self):
        return f"<TableRecord(id={self.id}, name='{self.table_name}')>"


class DatabaseManager:
    """
    数据库管理类
    封装所有数据库操作
    """
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，默认使用配置中的路径
        """
        if db_path is None:
            db_path = str(DATABASE_PATH)
        
        # 创建引擎（SQLite使用特殊配置以支持多线程）
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
            echo=False
        )
        
        # 创建所有表
        Base.metadata.create_all(self.engine)
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    # ==================== 标准参数操作 ====================
    
    def add_standard_param(self, param_name: str, param_name_en: str = None,
                           param_type: str = None, unit: str = None,
                           category: str = None, variants: List[str] = None) -> Optional[StandardParam]:
        """
        添加标准参数
        
        Args:
            param_name: 标准参数名（中文）
            param_name_en: 英文参数名/描述
            param_type: 器件类型
            unit: 单位
            category: 分类
            variants: 变体名称列表
            
        Returns:
            添加成功返回参数对象，失败返回None
        """
        session = self.get_session()
        try:
            # 检查是否已存在
            existing = session.query(StandardParam).filter_by(param_name=param_name).first()
            if existing:
                logger.warning(f"参数 '{param_name}' 已存在")
                return existing
            
            param = StandardParam(
                param_name=param_name,
                param_name_en=param_name_en,
                param_type=param_type,
                unit=unit,
                category=category
            )
            session.add(param)
            session.flush()  # 获取ID
            
            # 添加变体
            if variants:
                for variant_name in variants:
                    if variant_name and variant_name.strip():
                        variant = ParamVariant(
                            param_id=param.id,
                            variant_name=variant_name.strip()
                        )
                        session.add(variant)
            
            session.commit()
            logger.info(f"成功添加参数: {param_name}")
            return param
            
        except Exception as e:
            session.rollback()
            logger.error(f"添加参数失败: {e}")
            return None
        finally:
            session.close()
    
    def get_all_standard_params(self) -> List[StandardParam]:
        """获取所有标准参数"""
        session = self.get_session()
        try:
            params = session.query(StandardParam).all()
            return params
        finally:
            session.close()
    
    def get_standard_param_by_id(self, param_id: int) -> Optional[StandardParam]:
        """根据ID获取标准参数"""
        session = self.get_session()
        try:
            return session.query(StandardParam).filter_by(id=param_id).first()
        finally:
            session.close()
    
    def get_standard_param_by_name(self, param_name: str) -> Optional[StandardParam]:
        """根据名称获取标准参数"""
        session = self.get_session()
        try:
            return session.query(StandardParam).filter_by(param_name=param_name).first()
        finally:
            session.close()
    
    def update_standard_param(self, param_id: int, **kwargs) -> bool:
        """
        更新标准参数
        
        Args:
            param_id: 参数ID
            **kwargs: 要更新的字段
            
        Returns:
            更新成功返回True，否则False
        """
        session = self.get_session()
        try:
            param = session.query(StandardParam).filter_by(id=param_id).first()
            if not param:
                return False
            
            for key, value in kwargs.items():
                if hasattr(param, key):
                    setattr(param, key, value)
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"更新参数失败: {e}")
            return False
        finally:
            session.close()
    
    def delete_standard_param(self, param_id: int) -> bool:
        """删除标准参数"""
        session = self.get_session()
        try:
            param = session.query(StandardParam).filter_by(id=param_id).first()
            if param:
                session.delete(param)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"删除参数失败: {e}")
            return False
        finally:
            session.close()
    
    # ==================== 参数变体操作 ====================
    
    def add_variant(self, param_id: int, variant_name: str, vendor: str = None) -> Optional[ParamVariant]:
        """添加参数变体"""
        session = self.get_session()
        try:
            variant = ParamVariant(
                param_id=param_id,
                variant_name=variant_name,
                vendor=vendor
            )
            session.add(variant)
            session.commit()
            return variant
        except Exception as e:
            session.rollback()
            logger.error(f"添加变体失败: {e}")
            return None
        finally:
            session.close()
    
    def get_variants_by_param_id(self, param_id: int) -> List[ParamVariant]:
        """获取参数的所有变体"""
        session = self.get_session()
        try:
            return session.query(ParamVariant).filter_by(param_id=param_id).all()
        finally:
            session.close()
    
    def delete_variant(self, variant_id: int) -> bool:
        """删除变体"""
        session = self.get_session()
        try:
            variant = session.query(ParamVariant).filter_by(id=variant_id).first()
            if variant:
                session.delete(variant)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"删除变体失败: {e}")
            return False
        finally:
            session.close()
    
    def get_all_params_with_variants(self) -> List[Dict[str, Any]]:
        """获取所有参数及其变体（用于AI提示词生成）"""
        session = self.get_session()
        try:
            params = session.query(StandardParam).all()
            result = []
            for param in params:
                variants = session.query(ParamVariant).filter_by(param_id=param.id).all()
                result.append({
                    'id': param.id,
                    'param_name': param.param_name,
                    'param_name_en': param.param_name_en,
                    'param_type': param.param_type,
                    'unit': param.unit,
                    'category': param.category,
                    'variants': [v.variant_name for v in variants]
                })
            return result
        finally:
            session.close()
    
    # ==================== 解析结果操作 ====================
    
    def add_parse_result(self, pdf_name: str, pdf_path: str = None,
                         device_type: str = None, manufacturer: str = None,
                         opn: str = None, param_name: str = None,
                         param_value: str = None, test_condition: str = None,
                         is_success: bool = True, error_message: str = None,
                         user_id: int = None) -> Optional[ParseResult]:
        """添加解析结果（支持用户隔离）"""
        session = self.get_session()
        try:
            # 查找参数ID
            param_id = None
            if param_name:
                param = session.query(StandardParam).filter_by(param_name=param_name).first()
                if param:
                    param_id = param.id
            
            result = ParseResult(
                user_id=user_id,
                pdf_name=pdf_name,
                pdf_path=pdf_path,
                device_type=device_type,
                manufacturer=manufacturer,
                opn=opn,
                param_id=param_id,
                param_name=param_name,
                param_value=param_value,
                test_condition=test_condition,
                is_success=is_success,
                error_message=error_message
            )
            session.add(result)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"添加解析结果失败: {e}")
            return None
        finally:
            session.close()
    
    def get_parse_results_by_pdf(self, pdf_name: str, user_id: int = None) -> List[ParseResult]:
        """获取指定PDF的所有解析结果（按用户过滤）"""
        session = self.get_session()
        try:
            query = session.query(ParseResult).filter_by(pdf_name=pdf_name)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            return query.all()
        finally:
            session.close()
    
    def get_all_parse_results(self, user_id: int = None) -> List[ParseResult]:
        """获取所有解析结果（按用户过滤）"""
        session = self.get_session()
        try:
            query = session.query(ParseResult)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            return query.order_by(ParseResult.parse_time.desc()).all()
        finally:
            session.close()
    
    def delete_parse_results_by_pdf(self, pdf_name: str, user_id: int = None) -> bool:
        """删除指定PDF的解析结果（按用户过滤）"""
        session = self.get_session()
        try:
            query = session.query(ParseResult).filter_by(pdf_name=pdf_name)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            query.delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"删除解析结果失败: {e}")
            return False
        finally:
            session.close()
    
    def clear_all_parse_results(self, user_id: int = None) -> bool:
        """清空解析结果（按用户过滤）"""
        session = self.get_session()
        try:
            query = session.query(ParseResult)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            query.delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"清空解析结果失败: {e}")
            return False
        finally:
            session.close()
    
    # ==================== 解析日志操作 ====================
    
    def add_log(self, log_type: str, content: str, pdf_name: str = None) -> Optional[ParseLog]:
        """添加解析日志"""
        session = self.get_session()
        try:
            log = ParseLog(
                pdf_name=pdf_name,
                log_type=log_type,
                content=content
            )
            session.add(log)
            session.commit()
            return log
        except Exception as e:
            session.rollback()
            logger.error(f"添加日志失败: {e}")
            return None
        finally:
            session.close()
    
    def get_logs(self, log_type: str = None, pdf_name: str = None,
                 start_time: datetime = None, end_time: datetime = None,
                 limit: int = 100) -> List[ParseLog]:
        """
        获取日志（支持增强模糊搜索）
        
        Args:
            log_type: 日志类型筛选
            pdf_name: PDF文件名筛选（支持多关键词模糊匹配）
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
        """
        session = self.get_session()
        try:
            query = session.query(ParseLog)
            
            if log_type:
                query = query.filter_by(log_type=log_type)
            if pdf_name:
                # 使用增强模糊搜索
                fuzzy_filter = self._build_fuzzy_filter(ParseLog.pdf_name, pdf_name)
                if fuzzy_filter is not None:
                    query = query.filter(fuzzy_filter)
            if start_time:
                query = query.filter(ParseLog.create_time >= start_time)
            if end_time:
                query = query.filter(ParseLog.create_time <= end_time)
            
            return query.order_by(ParseLog.create_time.desc()).limit(limit).all()
        finally:
            session.close()
    
    def clear_logs(self) -> bool:
        """清空所有日志"""
        session = self.get_session()
        try:
            session.query(ParseLog).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"清空日志失败: {e}")
            return False
        finally:
            session.close()
    
    def get_parse_statistics(self, user_id: int = None) -> Dict[str, Any]:
        """
        获取解析统计信息
        
        Args:
            user_id: 用户ID，传入时只统计该用户的数据；为None时统计全部
        """
        session = self.get_session()
        try:
            base_query = session.query(ParseResult)
            if user_id is not None:
                base_query = base_query.filter(ParseResult.user_id == user_id)
            
            total = base_query.count()
            success = base_query.filter(ParseResult.is_success == True).count()
            failed = total - success
            
            # 获取唯一PDF数量（只算成功的）
            pdf_query = session.query(ParseResult.pdf_name).filter(ParseResult.is_success == True)
            if user_id is not None:
                pdf_query = pdf_query.filter(ParseResult.user_id == user_id)
            unique_pdfs = pdf_query.distinct().count()
            
            return {
                'total_params': success,  # 只统计成功提取的参数数量
                'success_count': success,
                'failed_count': failed,
                'unique_pdfs': unique_pdfs,
                'success_rate': round(success / total * 100, 2) if total > 0 else 0
            }
        finally:
            session.close()
    
    # ==================== 精细化查询与搜索功能 ====================
    
    def create_search_indexes(self):
        """
        创建搜索优化索引
        为常用搜索字段添加索引，提升查询性能
        """
        session = self.get_session()
        try:
            # 使用原生SQL创建索引
            for stmt in [
                "CREATE INDEX IF NOT EXISTS idx_parse_results_pdf_name ON parse_results(pdf_name)",
                "CREATE INDEX IF NOT EXISTS idx_parse_results_param_name ON parse_results(param_name)",
                "CREATE INDEX IF NOT EXISTS idx_parse_results_device_type ON parse_results(device_type)",
                "CREATE INDEX IF NOT EXISTS idx_standard_params_param_name ON standard_params(param_name)",
                "CREATE INDEX IF NOT EXISTS idx_param_variants_variant_name ON param_variants(variant_name)",
            ]:
                session.execute(text(stmt))
            session.commit()
            logger.info("搜索索引创建成功")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"创建索引失败: {e}")
            return False
        finally:
            session.close()
    
    def _expand_param_keyword_typos(self, keywords: List[str]) -> List[str]:
        """
        扩展参数关键词的常见易混淆写法，便于搜索（如 lsm -> 同时用 ism 匹配 Ism）。
        保持原关键词不变，只追加可能对应的正确写法。
        """
        seen = set()
        result = []
        # 首字母 I/l 易混淆（Ism vs lsm）
        for kw in keywords:
            k = kw.strip()
            if not k or k in seen:
                continue
            seen.add(k)
            result.append(k)
            k_lower = k.lower()
            if len(k_lower) >= 2:
                if k_lower[0] == 'l' and k_lower[1] != 'l':
                    alt = 'i' + k_lower[1:]
                    if alt not in seen:
                        seen.add(alt)
                        result.append(alt)
                elif k_lower[0] == 'i' and k_lower[1] != 'i':
                    alt = 'l' + k_lower[1:]
                    if alt not in seen:
                        seen.add(alt)
                        result.append(alt)
        return result
    
    def _build_fuzzy_filter(self, column, keyword: str):
        """
        构建模糊搜索过滤条件
        
        支持：
        1. 多关键词搜索（空格分隔，AND逻辑）
        2. 忽略大小写
        3. 支持部分匹配
        
        Args:
            column: 要搜索的数据库列
            keyword: 搜索关键词
            
        Returns:
            SQLAlchemy过滤条件
        """
        from sqlalchemy import and_, or_, func
        
        if not keyword or not keyword.strip():
            return None
        
        # 分割关键词（支持空格、逗号分隔）
        keywords = [k.strip() for k in keyword.replace(',', ' ').replace('，', ' ').split() if k.strip()]
        
        if not keywords:
            return None
        
        # 构建AND条件：所有关键词都必须匹配
        conditions = []
        for kw in keywords:
            # 使用LOWER实现忽略大小写（SQLite不区分大小写但其他数据库可能需要）
            conditions.append(func.lower(column).like(f'%{kw.lower()}%'))
        
        return and_(*conditions) if len(conditions) > 1 else conditions[0]
    
    def get_parsed_pdf_list(self, keyword: str = None, device_type: str = None, user_id: int = None) -> List[Dict[str, Any]]:
        """
        获取已解析的PDF列表（支持增强模糊搜索，按用户隔离）
        
        Args:
            keyword: PDF文件名关键词（支持多关键词，空格分隔，AND逻辑）
            device_type: 器件类型筛选
            user_id: 用户ID，用于数据隔离
            
        Returns:
            PDF信息列表，包含文件名、器件类型、参数数量、解析时间等
        """
        session = self.get_session()
        try:
            from sqlalchemy import func
            
            # 子查询：按PDF分组统计
            query = session.query(
                ParseResult.pdf_name,
                ParseResult.device_type,
                ParseResult.manufacturer,
                ParseResult.opn,
                func.count(ParseResult.id).label('param_count'),
                func.sum(func.cast(ParseResult.is_success, Integer)).label('success_count'),
                func.max(ParseResult.parse_time).label('parse_time')
            )
            
            # 按用户过滤
            if user_id is not None:
                query = query.filter(ParseResult.user_id == user_id)
            
            query = query.group_by(ParseResult.pdf_name)
            
            # 增强模糊搜索PDF文件名（支持多关键词）
            if keyword:
                fuzzy_filter = self._build_fuzzy_filter(ParseResult.pdf_name, keyword)
                if fuzzy_filter is not None:
                    query = query.filter(fuzzy_filter)
            
            # 筛选器件类型
            if device_type:
                query = query.filter(ParseResult.device_type == device_type)
            
            results = query.order_by(ParseResult.parse_time.desc()).all()
            
            pdf_list = []
            for row in results:
                pdf_list.append({
                    'pdf_name': row.pdf_name,
                    'device_type': row.device_type or '未知',
                    'manufacturer': row.manufacturer or '-',
                    'opn': row.opn or '-',
                    'param_count': row.param_count,
                    'success_count': row.success_count or 0,
                    'parse_time': row.parse_time
                })
            
            return pdf_list
        finally:
            session.close()
    
    def get_pdf_detail_params(self, pdf_name: str, user_id: int = None) -> Dict[str, Any]:
        """
        获取单个PDF的详细参数信息（精细化查看，按用户隔离）
        
        Args:
            pdf_name: PDF文件名
            user_id: 用户ID，用于数据隔离
            
        Returns:
            包含PDF基本信息、已提取参数、未提取参数的详细字典
        """
        session = self.get_session()
        try:
            # 获取该PDF的所有解析结果（按用户过滤）
            query = session.query(ParseResult).filter_by(pdf_name=pdf_name)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            results = query.all()
            
            if not results:
                return None
            
            # 获取所有标准参数
            all_params = session.query(StandardParam).all()
            all_param_names = {p.param_name for p in all_params}
            
            # 提取的参数
            extracted_params = []
            extracted_param_names = set()
            
            for result in results:
                if result.is_success and result.param_name:
                    extracted_param_names.add(result.param_name)
                    extracted_params.append({
                        'param_name': result.param_name,
                        'param_value': result.param_value or '-',
                        'test_condition': result.test_condition or '-',
                        'is_success': result.is_success
                    })
            
            # 未提取的参数
            missing_params = list(all_param_names - extracted_param_names)
            
            # 基本信息（取第一条记录）
            first_result = results[0]
            
            # 计算整体完整率
            total_params = len(all_param_names)
            extracted_count = len(extracted_param_names)
            completeness_rate = round(extracted_count / total_params * 100, 2) if total_params > 0 else 0
            
            # 关键参数完整性检查（从 extraction_rules.yaml 的 high 列表读取）
            key_params_total = 0
            key_params_extracted = 0
            key_params_missing: List[str] = []
            key_completeness_rate = 0.0
            
            try:
                import yaml
                from pathlib import Path
                rules_file = Path(__file__).parent / 'extraction_rules.yaml'
                if rules_file.exists():
                    with open(rules_file, 'r', encoding='utf-8') as f:
                        rules = yaml.safe_load(f) or {}
                    high_list = rules.get('extraction_priority', {}).get('high', []) or []
                    # 只统计当前参数库中存在的关键参数
                    key_set = {name for name in high_list if name in all_param_names}
                    key_params_total = len(key_set)
                    if key_set:
                        extracted_key = key_set & extracted_param_names
                        key_params_extracted = len(extracted_key)
                        key_params_missing = sorted(list(key_set - extracted_param_names))
                        key_completeness_rate = round(key_params_extracted / key_params_total * 100, 2)
            except Exception as e:
                # 日志中记录，但不影响主流程
                logger = logging.getLogger(__name__)
                logger.warning(f"计算关键参数完整率失败: {e}")
            
            return {
                'pdf_name': pdf_name,
                'device_type': first_result.device_type or '未知',
                'manufacturer': first_result.manufacturer or '-',
                'opn': first_result.opn or '-',
                'parse_time': first_result.parse_time,
                'total_params': total_params,
                'extracted_count': extracted_count,
                'completeness_rate': completeness_rate,
                'key_params_total': key_params_total,
                'key_params_extracted': key_params_extracted,
                'key_completeness_rate': key_completeness_rate,
                'key_missing_params': key_params_missing,
                'extracted_params': extracted_params,
                'missing_params': missing_params
            }
        finally:
            session.close()
    
    def search_params(self, pdf_keyword: str = None, param_keyword: str = None,
                      device_types: List[str] = None, page: int = 1, 
                      page_size: int = 50) -> Dict[str, Any]:
        """
        精准搜索参数（支持增强模糊搜索）
        
        搜索逻辑：
        1. 根据PDF文件名（支持多关键词模糊匹配）筛选出目标PDF列表
        2. 根据参数名关键词，匹配standard_params.param_name或param_variants.variant_name
        3. 从parse_results表中筛选交集结果
        
        Args:
            pdf_keyword: PDF文件名关键词（支持多关键词，空格分隔）
            param_keyword: 参数名关键词（匹配标准参数名或变体名，支持多关键词）
            device_types: 器件类型列表（筛选范围）
            page: 页码（从1开始）
            page_size: 每页数量
            
        Returns:
            包含搜索结果、总数、分页信息的字典
        """
        from sqlalchemy import func, or_
        
        session = self.get_session()
        try:
            # 基础查询
            query = session.query(ParseResult)
            
            # 步骤1：根据PDF文件名筛选（支持多关键词）
            if pdf_keyword:
                fuzzy_filter = self._build_fuzzy_filter(ParseResult.pdf_name, pdf_keyword)
                if fuzzy_filter is not None:
                    query = query.filter(fuzzy_filter)
            
            # 步骤2：根据参数名关键词筛选（支持多关键词）
            if param_keyword:
                # 分割关键词，并加入常见易混淆写法（如 lsm -> 同时匹配 Ism）
                raw_kws = [k.strip() for k in param_keyword.replace(',', ' ').replace('，', ' ').split() if k.strip()]
                param_keywords = list(self._expand_param_keyword_typos(raw_kws))
                
                if param_keywords:
                    # 查找匹配的标准参数ID
                    matching_param_ids = set()
                    
                    for kw in param_keywords:
                        # 匹配标准参数名
                        std_params = session.query(StandardParam).filter(
                            func.lower(StandardParam.param_name).like(f'%{kw.lower()}%')
                        ).all()
                        for p in std_params:
                            matching_param_ids.add(p.id)
                        
                        # 匹配变体名
                        variants = session.query(ParamVariant).filter(
                            func.lower(ParamVariant.variant_name).like(f'%{kw.lower()}%')
                        ).all()
                        for v in variants:
                            matching_param_ids.add(v.param_id)
                    
                    # 获取匹配的参数名列表
                    if matching_param_ids:
                        matching_param_names = session.query(StandardParam.param_name).filter(
                            StandardParam.id.in_(matching_param_ids)
                        ).all()
                        matching_names = [p[0] for p in matching_param_names]
                        
                        # 构建参数名过滤条件
                        param_conditions = [ParseResult.param_name.in_(matching_names)]
                        
                        # 同时直接模糊匹配param_name字段
                        for kw in param_keywords:
                            param_conditions.append(func.lower(ParseResult.param_name).like(f'%{kw.lower()}%'))
                        
                        query = query.filter(or_(*param_conditions))
                    else:
                        # 如果没有匹配到标准参数，直接搜索param_name
                        param_conditions = []
                        for kw in param_keywords:
                            param_conditions.append(func.lower(ParseResult.param_name).like(f'%{kw.lower()}%'))
                        query = query.filter(or_(*param_conditions))
            
            # 步骤3：筛选器件类型
            if device_types:
                query = query.filter(ParseResult.device_type.in_(device_types))
            
            # 只查询成功的结果
            query = query.filter(ParseResult.is_success == True)
            
            # 获取总数
            total_count = query.count()
            
            # 分页
            offset = (page - 1) * page_size
            results = query.order_by(
                ParseResult.pdf_name, 
                ParseResult.param_name
            ).offset(offset).limit(page_size).all()
            
            # 格式化结果
            search_results = []
            for result in results:
                search_results.append({
                    'pdf_name': result.pdf_name,
                    'device_type': result.device_type or '未知',
                    'manufacturer': result.manufacturer or '-',
                    'opn': result.opn or '-',
                    'param_name': result.param_name,
                    'param_value': result.param_value or '-',
                    'test_condition': result.test_condition or '-',
                    'parse_time': result.parse_time
                })
            
            # 计算分页信息
            total_pages = (total_count + page_size - 1) // page_size
            
            return {
                'results': search_results,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        finally:
            session.close()
    
    def get_device_types(self, user_id: int = None) -> List[str]:
        """获取所有已解析的器件类型（按用户过滤）"""
        session = self.get_session()
        try:
            query = session.query(ParseResult.device_type).distinct()
            if user_id is not None:
                query = query.filter(ParseResult.user_id == user_id)
            types = query.all()
            return [t[0] for t in types if t[0]]
        finally:
            session.close()
    
    def export_search_results(self, pdf_keyword: str = None, param_keyword: str = None,
                              device_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        导出搜索结果（无分页限制）
        
        Args:
            pdf_keyword: PDF文件名关键词
            param_keyword: 参数名关键词
            device_types: 器件类型列表
            
        Returns:
            完整的搜索结果列表
        """
        # 使用search_params但设置很大的page_size
        result = self.search_params(
            pdf_keyword=pdf_keyword,
            param_keyword=param_keyword,
            device_types=device_types,
            page=1,
            page_size=10000
        )
        return result['results']
    
    # ==================== 表格记录操作 ====================
    
    def add_table_record(self, table_name: str, device_type: str, pdf_count: int,
                         pdf_list: List[str], file_path: str, created_by: str = None) -> Optional[TableRecord]:
        """
        添加表格记录
        
        Args:
            table_name: 表格文件名
            device_type: 器件类型
            pdf_count: PDF文件数量
            pdf_list: PDF文件列表
            file_path: 表格文件路径
            created_by: 创建用户
            
        Returns:
            创建的表格记录对象
        """
        import json
        session = self.get_session()
        try:
            record = TableRecord(
                table_name=table_name,
                device_type=device_type,
                pdf_count=pdf_count,
                pdf_list=json.dumps(pdf_list, ensure_ascii=False),
                file_path=file_path,
                created_by=created_by
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info(f"表格记录已添加: {table_name}")
            return record
        except Exception as e:
            session.rollback()
            logger.error(f"添加表格记录失败: {e}")
            return None
        finally:
            session.close()
    
    def get_table_records(self, device_type: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取表格记录列表
        
        Args:
            device_type: 筛选器件类型
            limit: 返回数量限制
            
        Returns:
            表格记录列表
        """
        import json
        session = self.get_session()
        try:
            query = session.query(TableRecord)
            
            if device_type:
                query = query.filter_by(device_type=device_type)
            
            records = query.order_by(TableRecord.create_time.desc()).limit(limit).all()
            
            result = []
            for r in records:
                result.append({
                    'id': r.id,
                    'table_name': r.table_name,
                    'device_type': r.device_type,
                    'pdf_count': r.pdf_count,
                    'pdf_list': json.loads(r.pdf_list) if r.pdf_list else [],
                    'file_path': r.file_path,
                    'create_time': r.create_time,
                    'created_by': r.created_by or '-'
                })
            
            return result
        finally:
            session.close()
    
    def get_table_record_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取表格记录"""
        import json
        session = self.get_session()
        try:
            record = session.query(TableRecord).filter_by(id=record_id).first()
            if record:
                return {
                    'id': record.id,
                    'table_name': record.table_name,
                    'device_type': record.device_type,
                    'pdf_count': record.pdf_count,
                    'pdf_list': json.loads(record.pdf_list) if record.pdf_list else [],
                    'file_path': record.file_path,
                    'create_time': record.create_time,
                    'created_by': record.created_by or '-'
                }
            return None
        finally:
            session.close()
    
    def delete_table_record(self, record_id: int) -> bool:
        """
        删除表格记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否删除成功
        """
        import os
        session = self.get_session()
        try:
            record = session.query(TableRecord).filter_by(id=record_id).first()
            if record:
                # 删除本地文件
                if os.path.exists(record.file_path):
                    try:
                        os.remove(record.file_path)
                        logger.info(f"已删除表格文件: {record.file_path}")
                    except Exception as e:
                        logger.warning(f"删除文件失败: {e}")
                
                # 删除数据库记录
                session.delete(record)
                session.commit()
                logger.info(f"表格记录已删除: ID={record_id}")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"删除表格记录失败: {e}")
            return False
        finally:
            session.close()
    
    def get_pdf_list_by_device_type(self, device_type: str, user_id: int = None) -> List[str]:
        """
        获取指定器件类型的所有已解析PDF文件名（按用户过滤）
        
        Args:
            device_type: 器件类型
            user_id: 用户ID，用于数据隔离
            
        Returns:
            PDF文件名列表（去重）
        """
        session = self.get_session()
        try:
            query = session.query(ParseResult.pdf_name).filter(
                ParseResult.device_type == device_type
            )
            if user_id is not None:
                query = query.filter(ParseResult.user_id == user_id)
            results = query.distinct().all()
            return [r[0] for r in results]
        finally:
            session.close()
    
    def _get_param_order_from_yaml(self, device_type: str) -> List[str]:
        """从器件类型对应的YAML加载参数列顺序（与Excel严格对齐）"""
        type_map = {'Si MOSFET': 'si_mosfet', 'SiC MOSFET': 'sic_mosfet', 'IGBT': 'igbt'}
        key = type_map.get(device_type, 'si_mosfet')
        config_path = Path(__file__).parent / 'device_configs' / f'{key}.yaml'
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            groups = data.get('groups', {})
            return [p['name'] for g, params in groups.items() for p in params]
        except Exception as e:
            logger.warning(f"加载YAML列顺序失败 {config_path}: {e}")
            return []

    def get_params_for_table(self, device_type: str, pdf_list: List[str], user_id: int = None) -> Dict[str, Any]:
        """
        获取用于生成表格的参数数据（按用户过滤）
        
        按「器件一行、参数一列」整理数据：
        - 行：选中的PDF文件
        - 列：该器件类型的所有标准参数（顺序来自YAML，与Excel严格对齐）
        - 单元格：参数值（含测试条件备注），未提取标为「未提取」
        
        增强匹配逻辑：
        - 精确匹配标准参数名
        - 模糊匹配（忽略大小写、空格）
        - 变体名匹配
        
        Args:
            device_type: 器件类型
            pdf_list: PDF文件列表
            user_id: 用户ID，用于数据隔离
            
        Returns:
            包含表头和数据行的字典
        """
        session = self.get_session()
        try:
            # 列顺序优先从YAML加载（与Excel严格对齐），否则回退到数据库
            param_names = self._get_param_order_from_yaml(device_type)
            if not param_names:
                all_params = session.query(StandardParam).order_by(StandardParam.id).all()
                param_names = [p.param_name for p in all_params]
            else:
                all_params = session.query(StandardParam).all()
            
            # 构建参数名映射表（用于模糊匹配）
            # key: 标准化后的名称（小写、去空格）, value: 原始标准参数名
            param_name_map = {}
            for p in all_params:
                # 标准参数名的标准化形式
                normalized = p.param_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                param_name_map[normalized] = p.param_name
                param_name_map[p.param_name] = p.param_name  # 精确匹配
                
                # 添加英文名映射（关键修复！）
                if p.param_name_en:
                    param_name_map[p.param_name_en] = p.param_name  # 精确匹配英文名
                    en_normalized = p.param_name_en.lower().replace(' ', '').replace('_', '').replace('-', '')
                    param_name_map[en_normalized] = p.param_name  # 标准化英文名
                
                # 添加变体名映射
                variants = session.query(ParamVariant).filter_by(param_id=p.id).all()
                for v in variants:
                    variant_normalized = v.variant_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                    param_name_map[variant_normalized] = p.param_name
                    param_name_map[v.variant_name] = p.param_name  # 精确匹配变体名
            
            # 旧参数名 -> 新参数名（兼容已存储的旧数据）
            legacy_mapping = {
                # Si/SiC MOSFET: RDS(on) 与 Ron 互为别名
                'RDS(on) 10V_type': 'Ron 10V_type', 'RDS(on) 10V_max': 'Ron 10V_max',
                'RDS(on) 4.5V_type': 'Ron 4.5V_type', 'RDS(on) 4.5V_max': 'Ron 4.5V_max',
                'RDS(on) 2.5V_type': 'Ron 2.5V_type', 'RDS(on) 2.5V_max': 'Ron 2.5V_max',
                # IGBT 旧名 -> 新名（带单位后缀的 Excel 列名）
                'Cies': 'Cies（pF）', 'Coes': 'Coes（pF）', 'Cres': 'Cres（pF）',
                'tdon 25℃': 'tdon 25℃（ns）', 'tdon 175℃': 'tdon 175℃（ns）',
                'tr 25℃': 'tr 25℃（ns）', 'tr 175℃': 'tr175℃（ns）',
                'tdoff 25℃': 'tdoff 25℃（ns）', 'tdoff 175℃': 'tdoff 175℃（ns）',
                'tf 25℃': 'tf 25℃（ns）', 'tf 175℃': 'tf 175℃（ns）',
                'trr 25℃': 'trr 25℃（ns）',
                'Eon 25℃': 'Eon 25℃（uJ）', 'Eon 175℃': 'Eon 175℃（uJ）',
                'Eoff 25℃': 'Eoff（uJ）', 'Eoff 175℃': 'Eoff 175℃（uJ）',
                'Ets 25℃': 'Ets 25℃（uJ）', 'Ets 175℃': 'Ets 175℃（uJ）',
                'QG_IGBT': 'QG(nc)', 'QGE': 'QGE(nc)', 'QGC': 'QGC(nc)',
                'Qrr 25℃_IGBT': 'Qrr 25℃（uC）', 'Qrr 175℃_IGBT': 'Qrr 175℃',
            }
            # 数据库 param 名 -> YAML 列名（用于行数据 key，保证与 YAML 列一致）
            db_to_column = {'gfs_IGBT': 'gfs'}
            for old_name, new_name in legacy_mapping.items():
                if new_name in [p.param_name for p in all_params]:
                    param_name_map[old_name] = new_name
                    # 标准化形式也映射
                    old_normalized = old_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                    param_name_map[old_normalized] = new_name
            
            # 获取每个PDF的解析结果
            table_data = []
            
            for pdf_name in pdf_list:
                # 查询该PDF的所有解析结果（按用户过滤）
                query = session.query(ParseResult).filter(
                    ParseResult.pdf_name == pdf_name
                )
                if user_id is not None:
                    query = query.filter(ParseResult.user_id == user_id)
                results = query.all()
                
                # 构建参数值映射（使用标准参数名作为key）
                param_values = {}
                opn = '-'
                manufacturer = '-'
                
                # 即使没有解析结果，也继续处理（会生成一行空数据）
                for r in results:
                    if r.param_name:
                        # 参数值：只保留纯数值+单位，测试条件不拼接
                        value = r.param_value or '-'
                        
                        # 尝试匹配到标准参数名
                        matched_name = None
                        
                        # 1. 精确匹配
                        if r.param_name in param_name_map:
                            matched_name = param_name_map[r.param_name]
                        else:
                            # 2. 标准化后匹配
                            normalized_name = r.param_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                            if normalized_name in param_name_map:
                                matched_name = param_name_map[normalized_name]
                        
                        if matched_name:
                            # 用 YAML 列名作为 key，便于与 param_names 对齐（如 gfs_IGBT -> gfs）
                            store_key = db_to_column.get(matched_name, matched_name)
                            if store_key in param_names:
                                param_values[store_key] = value
                            else:
                                param_values[matched_name] = value
                        else:
                            param_values[r.param_name] = value
                    
                    # 提取型号和厂家
                    if r.opn:
                        opn = r.opn
                    if r.manufacturer:
                        manufacturer = r.manufacturer
                
                # 构建行数据（所有列都从参数库获取）
                row = {}
                
                # 从解析结果中获取更多基本信息
                device_type = '-'
                package = '-'
                for r in results:
                    if r.device_type:
                        device_type = r.device_type
                    # 尝试获取封装信息
                    if r.param_name and '封装' in r.param_name and r.param_value:
                        package = r.param_value
                
                # 填充各参数列
                for param_name in param_names:
                    if param_name in ('PDF文件名', '文件名'):
                        row[param_name] = pdf_name
                    elif param_name == '厂家':
                        # 优先使用解析结果中的厂家
                        row[param_name] = manufacturer if manufacturer != '-' else param_values.get(param_name, '-')
                    elif param_name == 'OPN':
                        # 优先使用解析结果中的OPN
                        row[param_name] = opn if opn != '-' else param_values.get(param_name, '-')
                    elif param_name == '技术':
                        # 技术类型可以从device_type推断
                        row[param_name] = param_values.get(param_name, device_type if device_type != '-' else '-')
                    elif param_name == '封装' or param_name == '厂家封装名':
                        row[param_name] = param_values.get(param_name, package if package != '-' else '-')
                    else:
                        row[param_name] = param_values.get(param_name, '-')
                
                table_data.append(row)
            
            # 构建表头（完全按照参数库顺序，与Excel一致）
            headers = param_names
            
            return {
                'headers': headers,
                'data': table_data,
                'param_count': len(param_names),
                'pdf_count': len(pdf_list)
            }
        finally:
            session.close()
    
    def diagnose_param_matching(self, pdf_name: str) -> Dict[str, Any]:
        """
        诊断参数匹配情况
        
        用于调试：显示数据库中存储的参数名与标准参数库的匹配情况
        
        Args:
            pdf_name: PDF文件名
            
        Returns:
            诊断结果字典
        """
        session = self.get_session()
        try:
            # 获取所有标准参数
            all_params = session.query(StandardParam).all()
            standard_names = {p.param_name for p in all_params}
            
            # 构建变体名到标准名的映射
            variant_to_standard = {}
            for p in all_params:
                variants = session.query(ParamVariant).filter_by(param_id=p.id).all()
                for v in variants:
                    variant_to_standard[v.variant_name] = p.param_name
            
            # 获取该PDF的解析结果
            results = session.query(ParseResult).filter(
                ParseResult.pdf_name == pdf_name,
                ParseResult.is_success == True
            ).all()
            
            matched = []  # 完全匹配的参数
            variant_matched = []  # 通过变体匹配的参数
            unmatched = []  # 未匹配的参数
            
            for r in results:
                if r.param_name:
                    if r.param_name in standard_names:
                        matched.append({
                            'stored_name': r.param_name,
                            'value': r.param_value,
                            'match_type': '精确匹配'
                        })
                    elif r.param_name in variant_to_standard:
                        variant_matched.append({
                            'stored_name': r.param_name,
                            'standard_name': variant_to_standard[r.param_name],
                            'value': r.param_value,
                            'match_type': '变体匹配'
                        })
                    else:
                        # 尝试模糊匹配
                        normalized = r.param_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                        fuzzy_match = None
                        for std_name in standard_names:
                            std_normalized = std_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                            if normalized == std_normalized:
                                fuzzy_match = std_name
                                break
                        
                        if fuzzy_match:
                            variant_matched.append({
                                'stored_name': r.param_name,
                                'standard_name': fuzzy_match,
                                'value': r.param_value,
                                'match_type': '模糊匹配'
                            })
                        else:
                            unmatched.append({
                                'stored_name': r.param_name,
                                'value': r.param_value,
                                'match_type': '未匹配'
                            })
            
            return {
                'pdf_name': pdf_name,
                'total_params': len(results),
                'matched_count': len(matched),
                'variant_matched_count': len(variant_matched),
                'unmatched_count': len(unmatched),
                'matched': matched,
                'variant_matched': variant_matched,
                'unmatched': unmatched,
                'standard_param_count': len(standard_names)
            }
        finally:
            session.close()

    # ==================== 器件筛选功能 ====================

    @staticmethod
    def _extract_number(value_str: str) -> Optional[float]:
        """
        从参数值字符串中提取第一个数值。
        支持 "100"、"10.5"、"-40"、"≤100"、"100V"、"1.2 mΩ" 等格式。
        返回 None 表示无法提取。
        """
        if not value_str or not isinstance(value_str, str):
            return None
        value_str = value_str.strip()
        # 跳过明显非数值的内容
        if value_str in ('-', 'N/A', '', '—', '/'):
            return None
        match = re.search(r'[-+]?\d*\.?\d+', value_str)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    def get_available_filter_params(self, user_id: int = None) -> List[Dict[str, Any]]:
        """
        获取当前用户已提取过的、可用于数值筛选的参数列表。
        返回参数名、英文名、单位，供前端选择器使用。
        """
        session = self.get_session()
        try:
            from sqlalchemy import func, distinct

            # 查询该用户已提取的不重复参数名
            query = session.query(
                ParseResult.param_name
            ).filter(
                ParseResult.is_success == True,
                ParseResult.param_value.isnot(None),
                ParseResult.param_value != '',
                ParseResult.param_value != '-'
            )
            if user_id is not None:
                query = query.filter(ParseResult.user_id == user_id)

            param_names = [row[0] for row in query.distinct().all() if row[0]]

            # 跳过基本信息类参数（非数值型）
            skip_params = {'PDF文件名', '厂家', 'OPN', '厂家封装名', '技术', '封装',
                           '特殊功能', '极性', 'Product Status', '认证', '安装', 'ESD',
                           '预算价格€/1k', 'Qg测试条件', 'Ciss测试条件',
                           '开关时间测试条件', 'Qrr测试条件', 'EAS测试条件', 'IDM限制条件'}

            # 查标准参数表获取 unit/英文名
            all_standard = session.query(StandardParam).all()
            std_map = {p.param_name: p for p in all_standard}

            result = []
            for pn in param_names:
                if pn in skip_params:
                    continue
                sp = std_map.get(pn)
                unit = sp.unit if sp else ''
                param_name_en = sp.param_name_en if sp else ''
                category = sp.category if sp else ''
                result.append({
                    'param_name': pn,
                    'param_name_en': param_name_en,
                    'unit': unit or '',
                    'category': category or '',
                })

            # 按分类排序，同分类内按参数名排序
            result.sort(key=lambda x: (x['category'], x['param_name']))
            return result
        finally:
            session.close()

    def filter_devices_by_param_ranges(
        self,
        conditions: List[Dict[str, Any]],
        user_id: int = None,
        device_type: str = None
    ) -> Dict[str, Any]:
        """
        按参数范围筛选器件。

        Args:
            conditions: 筛选条件列表，每项:
                {'param_name': str, 'min_val': float|None, 'max_val': float|None}
            user_id: 用户ID（数据隔离）
            device_type: 可选的器件类型过滤

        Returns:
            {
                'devices': [
                    {
                        'pdf_name': str,
                        'manufacturer': str,
                        'opn': str,
                        'device_type': str,
                        'params': {param_name: param_value, ...}  # 所有参数
                    },
                    ...
                ],
                'total_found': int,
                'total_checked': int,
                'param_columns': [str, ...]  # 所有出现过的参数名（有序）
            }
        """
        session = self.get_session()
        try:
            # 1. 查询所有解析结果
            query = session.query(ParseResult).filter(
                ParseResult.is_success == True
            )
            if user_id is not None:
                query = query.filter(ParseResult.user_id == user_id)
            if device_type:
                query = query.filter(ParseResult.device_type == device_type)

            all_results = query.all()

            # 2. 按 pdf_name 分组
            devices = {}  # pdf_name -> {info + params}
            for r in all_results:
                if not r.pdf_name:
                    continue
                if r.pdf_name not in devices:
                    devices[r.pdf_name] = {
                        'pdf_name': r.pdf_name,
                        'manufacturer': r.manufacturer or '-',
                        'opn': r.opn or '-',
                        'device_type': r.device_type or '-',
                        'params': {}
                    }
                if r.param_name and r.param_value:
                    devices[r.pdf_name]['params'][r.param_name] = r.param_value

            # 3. 筛选：检查每个器件是否满足全部条件
            matched_devices = []
            total_checked = len(devices)

            for pdf_name, device in devices.items():
                all_match = True
                for cond in conditions:
                    pn = cond['param_name']
                    min_val = cond.get('min_val')
                    max_val = cond.get('max_val')

                    # 如果没有设定任何范围，跳过这个条件
                    if min_val is None and max_val is None:
                        continue

                    # 获取该器件的参数值
                    raw_value = device['params'].get(pn)
                    num = self._extract_number(raw_value)

                    if num is None:
                        # 没有该参数或无法提取数值 → 不满足
                        all_match = False
                        break

                    if min_val is not None and num < min_val:
                        all_match = False
                        break
                    if max_val is not None and num > max_val:
                        all_match = False
                        break

                if all_match:
                    matched_devices.append(device)

            # 4. 收集所有出现过的参数列名（有序）
            param_columns_set = set()
            for d in matched_devices:
                param_columns_set.update(d['params'].keys())

            # 按标准参数表的顺序排列
            all_standard = session.query(StandardParam).all()
            std_order = {p.param_name: idx for idx, p in enumerate(all_standard)}
            param_columns = sorted(
                param_columns_set,
                key=lambda x: std_order.get(x, 9999)
            )

            return {
                'devices': matched_devices,
                'total_found': len(matched_devices),
                'total_checked': total_checked,
                'param_columns': param_columns,
            }
        finally:
            session.close()