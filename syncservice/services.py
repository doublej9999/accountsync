import os
import requests
import json
import hashlib
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
import logging
from typing import Dict, Any, Optional

try:
    import pypinyin
    PYPINYIN_AVAILABLE = True
except ImportError:
    PYPINYIN_AVAILABLE = False

from syncservice.models import HrPerson, DepartmentMapping, AccountCreationTask, AccountCreationLog, SyncConfig

logger = logging.getLogger(__name__)


class AccountCreationService:
    """账号创建服务"""

    def __init__(self):
        self.timeout = 30  # 默认超时时间
        self._token_cache = {}  # token 缓存

    def create_account(self, person: HrPerson, account_type: str, department_code: str) -> Dict[str, Any]:
        """创建账号"""
        if account_type == 'idaas':
            return self._create_idaas_account(person, department_code)
        elif account_type == 'welink':
            return self._create_welink_account(person, department_code)
        elif account_type == 'email':
            return self._create_email_account(person)
        else:
            raise ValueError(f"不支持的账号类型: {account_type}")

    def _create_idaas_account(self, person: HrPerson, department_code: str) -> Dict[str, Any]:
        """创建 IDAAS 账号"""
        try:
            # 获取企业级 token
            enterprise_token = self._get_idaas_enterprise_token()

            # 获取部门映射
            department_mapping = self._get_department_mapping(department_code)
            # 检查 OU 是否可用
            if not department_mapping or not department_mapping.ou:
                raise Exception(f"部门代码 {department_code} 对应的 OU 不存在，无法创建账号")

            # 生成用户名和邮箱
            username = self._generate_username(person.employee_number, person.full_name)
            email = self._generate_unique_email(person.full_name, person.employee_number)

            # 构建请求数据
            data = {
                "userInfo": {
                    "employeeNumber": person.employee_number,
                    "name": person.full_name,
                    "englishName": self._convert_to_pinyin(person.full_name),
                    "userName": username,
                    "userType": "supplier",
                    "email": email,
                    "mobileCountryCode": "+86",
                    "mobile": person.telephone_number1 or person.telephone_number2 or "",
                    "userExtends": {
                        "workArea": "China",
                        "ou": department_mapping.ou
                    }
                }
            }

            # 发送创建请求
            enterprise_id = ConfigService.get_config('idaas_enterprise_id')
            url = f"https://apig.hieds.net/api/idaas/idm-openapi/enterprise/{enterprise_id}/user/onboarding"

            headers = {
                'Authorization': enterprise_token,
                'Content-Type': 'application/json'
            }

            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            if result.get('code') != 201:
                raise Exception(f"IDAAS API 返回错误: {result}")

            return {
                'account_identifier': username,
                'email': email,
                'service_response': result,
                'department_mapping': {
                    'idata_code': department_code,
                    'idaas_code': department_mapping.idaas_departmentcode if department_mapping else None,
                    'ou': department_mapping.ou if department_mapping else None
                }
            }

        except Exception as e:
            logger.error(f"创建 IDAAS 账号失败: {person.employee_number}, 错误: {e}")
            raise

    def _create_welink_account(self, person: HrPerson, department_code: str) -> Dict[str, Any]:
        """创建 Welink 账号"""
        try:
            # 获取 Welink token
            welink_token = self._get_welink_token()

            # 获取部门映射
            department_mapping = self._get_department_mapping(department_code)

            # 构建请求数据
            data = {
                "corpUserId": person.employee_number,
                "userNameCn": person.full_name,
                "mobileNumber": person.telephone_number1 or person.telephone_number2 or "",
                "corpDeptCodes": [department_mapping.idaas_departmentcode] if department_mapping else ["WW10010"],
                "personType": "外包",
                "userEmail": self._generate_unique_email(person.full_name, person.employee_number),
                "employeeId": person.employee_number
            }

            # 发送创建请求
            url = "https://open.welink.huaweicloud.com/api/contact/v1/user/create"
            headers = {
                'x-wlk-Authorization': welink_token,
                'Content-Type': 'application/json'
            }

            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            if result.get('code') != "0":
                raise Exception(f"Welink API 返回错误: {result}")

            return {
                'account_identifier': person.employee_number,
                'service_response': result,
                'department_mapping': {
                    'idata_code': department_code,
                    'welink_dept_code': department_mapping.idaas_departmentcode if department_mapping else None
                }
            }

        except Exception as e:
            logger.error(f"创建 Welink 账号失败: {person.employee_number}, 错误: {e}")
            raise

    def _create_email_account(self, person: HrPerson) -> Dict[str, Any]:
        """启用邮箱账号"""
        try:
            # 获取邮箱地址（应该已经在 IDAAS 创建时生成）
            email = self._generate_unique_email(person.full_name, person.employee_number)
            username = self._generate_username(person.employee_number, person.full_name)

            # 构建请求数据
            data = {
                "EnableMailboxList": [
                    {
                        "SAMAccountName": username,
                        "Alias": self._convert_to_pinyin(person.full_name).lower()
                    }
                ]
            }

            # 发送启用请求
            url = "http://172.20.64.24:8080/api/Exchange/EnableMailbox"
            headers = {
                'Authorization': ConfigService.get_config('email_auth_token', 'abcdefghijklmnoprstuvwxyz'),
                'Content-Type': 'application/json'
            }

            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            if result.get('code') != "200":
                raise Exception(f"邮箱服务 API 返回错误: {result}")

            return {
                'account_identifier': email,
                'username': username,
                'alias': self._convert_to_pinyin(person.full_name).lower(),
                'service_response': result
            }

        except Exception as e:
            logger.error(f"启用邮箱账号失败: {person.employee_number}, 错误: {e}")
            raise

    def _get_idaas_enterprise_token(self) -> str:
        """获取 IDAAS 企业级 token"""
        cache_key = 'idaas_enterprise_token'
        cached_token = self._get_cached_token(cache_key)

        if cached_token:
            return cached_token

        url = "https://apig.hieds.net/api/iam/auth/enterprise-token"
        headers = {'Content-Type': 'application/json'}

        data = {
            "data": {
                "type": "token",
                "attributes": {
                    "account": ConfigService.get_config('idaas_account'),
                    "secret": ConfigService.get_config('idaas_secret')
                }
            }
        }

        response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        result = response.json()
        if result.get('code') != "201":
            raise Exception(f"获取 IDAAS token 失败: {result}")

        token = result['access_token']
        expires_in = result.get('expires_in', 86399)

        # 缓存 token（提前5分钟过期）
        self._cache_token(cache_key, token, expires_in - 300)

        return token

    def _get_welink_token(self) -> str:
        """获取 Welink token"""
        cache_key = 'welink_token'
        cached_token = self._get_cached_token(cache_key)

        if cached_token:
            return cached_token

        url = "https://apig.hieds.net/api/auth/v2/tickets"
        headers = {'Content-Type': 'application/json'}

        data = {
            "client_id": ConfigService.get_config('welink_client_id'),
            "client_secret": ConfigService.get_config('welink_client_secret')
        }

        response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        result = response.json()
        if result.get('code') != "0":
            raise Exception(f"获取 Welink token 失败: {result}")

        token = result['access_token']
        expires_in = result.get('expires_in', 7200)

        # 缓存 token（提前5分钟过期）
        self._cache_token(cache_key, token, expires_in - 300)

        return token

    def _get_department_mapping(self, department_code: str) -> Optional[DepartmentMapping]:
        """获取部门映射"""
        try:
            return DepartmentMapping.objects.get(idata_departmentcode=department_code)
        except DepartmentMapping.DoesNotExist:
            logger.warning(f"未找到部门映射: {department_code}")
            return None

    def _convert_to_pinyin(self, chinese_name: str) -> str:
        """将中文名转换为拼音"""
        if not PYPINYIN_AVAILABLE:
            # 如果没有 pypinyin，使用简单的替换
            logger.warning("pypinyin 未安装，使用简化的拼音转换")
            return chinese_name  # 返回原名作为降级方案

        try:
            pinyin_list = pypinyin.lazy_pinyin(chinese_name, style=pypinyin.Style.NORMAL)
            return ''.join(pinyin_list)
        except Exception as e:
            logger.error(f"拼音转换失败: {chinese_name}, 错误: {e}")
            return chinese_name

    def _generate_username(self, employee_number: str, full_name: str) -> str:
        """生成用户名：拼音首字母 + 员工编号"""
        pinyin = self._convert_to_pinyin(full_name)
        initials = ''.join([word[0] for word in pinyin.split() if word])
        return f"{initials}{employee_number}"

    def _generate_unique_email(self, full_name: str, employee_number: str) -> str:
        """生成唯一的邮箱地址"""
        base_email = self._convert_to_pinyin(full_name).lower()
        domain = ConfigService.get_config('email_domain', '@qq.com')

        # 检查是否存在相同拼音的人
        existing_emails = set()
        persons_with_same_pinyin = HrPerson.objects.filter(
            person_pinyin_name__icontains=base_email.split('.')[0]
        ).exclude(employee_number=employee_number)

        for person in persons_with_same_pinyin:
            if person.email_address and person.email_address.startswith(base_email.split('.')[0]):
                existing_emails.add(person.email_address)

        # 生成唯一邮箱
        if f"{base_email}{domain}" not in existing_emails:
            return f"{base_email}{domain}"

        # 如果有重复，添加序号
        counter = 2
        while True:
            candidate = f"{base_email}{counter}{domain}"
            if candidate not in existing_emails:
                return candidate
            counter += 1

    def _get_cached_token(self, cache_key: str) -> Optional[str]:
        """获取缓存的 token"""
        if cache_key in self._token_cache:
            token_data = self._token_cache[cache_key]
            if timezone.now() < token_data['expires_at']:
                return token_data['token']
            else:
                # token 已过期，删除缓存
                del self._token_cache[cache_key]
        return None

    def _cache_token(self, cache_key: str, token: str, expires_in: int):
        """缓存 token"""
        self._token_cache[cache_key] = {
            'token': token,
            'expires_at': timezone.now() + timedelta(seconds=expires_in)
        }


class ConfigService:
    """配置管理服务 - 统一管理SyncConfig和环境变量"""

    @staticmethod
    def get_config(key: str, default: str = None) -> str:
        """获取配置值，优先从SyncConfig获取，后备到环境变量"""
        try:
            config = SyncConfig.objects.get(key=key)
            return config.value
        except SyncConfig.DoesNotExist:
            # 后备到环境变量（保持向后兼容）
            env_key = key.upper()
            return os.getenv(env_key, default)

    @staticmethod
    def get_bool_config(key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        value = ConfigService.get_config(key, str(default).lower())
        return value.lower() == 'true'

    @staticmethod
    def get_int_config(key: str, default: int = 0) -> int:
        """获取整数配置"""
        value = ConfigService.get_config(key, str(default))
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def get_json_config(key: str, default: Any = None) -> Any:
        """获取JSON配置"""
        value = ConfigService.get_config(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return default
