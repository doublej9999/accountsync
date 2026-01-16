import os
import requests
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings
import time

from syncservice.models import HrPerson, HrPersonAccount, SyncConfig


class Command(BaseCommand):
    help = '同步人员数据从HIEDS API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-full-sync',
            action='store_true',
            help='强制全量同步，忽略上次同步时间',
        )
        parser.add_argument(
            '--page-size',
            type=int,
            default=20,
            help='每页大小，默认20',
        )

    def handle(self, *args, **options):
        force_full_sync = options['force_full_sync']
        page_size = options['page_size']

        self.stdout.write('开始同步人员数据...')

        try:
            # 获取配置
            account = os.getenv('HIEDS_ACCOUNT')
            secret = os.getenv('HIEDS_SECRET')
            project = os.getenv('HIEDS_PROJECT')
            enterprise = os.getenv('HIEDS_ENTERPRISE')
            person_project_id = os.getenv('HIEDS_PERSON_PROJECT_ID')
            tenant_id = os.getenv('HIEDS_TENANT_ID')
            page_size = int(os.getenv('HIEDS_PAGE_SIZE', page_size))

            if not all([account, secret, project, enterprise, person_project_id, tenant_id]):
                raise CommandError('缺少必要的环境变量配置')

            # 获取token
            self.stdout.write('获取访问token...')
            token = self._get_token(account, secret, project, enterprise)
            if not token:
                raise CommandError('获取token失败')

            # 获取上次同步时间
            last_sync_time = None
            if not force_full_sync:
                last_sync_time_str = SyncConfig.get_config('last_sync_time')
                if last_sync_time_str:
                    last_sync_time = datetime.fromisoformat(last_sync_time_str.replace('Z', '+00:00'))
                    self.stdout.write(f'增量同步，上次同步时间: {last_sync_time}')

            # 分页获取人员数据
            total_synced = 0
            cur_page = 1

            while True:
                self.stdout.write(f'获取第{cur_page}页数据...')

                data = self._fetch_persons_page(token, person_project_id, tenant_id, page_size, cur_page, last_sync_time)

                if not data or 'result' not in data:
                    self.stdout.write(self.style.WARNING(f'第{cur_page}页无数据'))
                    break

                persons = data['result']
                if not persons:
                    break

                # 保存人员数据
                synced_count = self._save_persons(persons)
                total_synced += synced_count

                # 检查是否还有更多数据
                page_info = data.get('pageInfo', {})
                total_pages = page_info.get('totalPages', 0)

                if cur_page >= total_pages:
                    break

                cur_page += 1

                # 添加延迟避免API限流
                time.sleep(1)

            # 更新同步状态
            SyncConfig.set_config('last_sync_time', timezone.now().isoformat(), '上次同步时间')
            SyncConfig.set_config('last_sync_status', 'success', '上次同步状态')
            SyncConfig.set_config('total_persons', str(HrPerson.objects.count()), '总人员数')

            self.stdout.write(
                self.style.SUCCESS(f'同步完成，共同步 {total_synced} 条记录，当前总人数: {HrPerson.objects.count()}')
            )

        except Exception as e:
            # 记录失败状态
            SyncConfig.set_config('last_sync_status', f'failed: {str(e)}', '上次同步状态')
            raise CommandError(f'同步失败: {str(e)}')

    def _get_token(self, account, secret, project, enterprise):
        """获取访问token"""
        url = 'https://apig.hieds.net/api/iam/auth/token'
        headers = {'Content-Type': 'application/json'}

        data = {
            "data": {
                "type": "JWT-Token",
                "attributes": {
                    "method": "CREATE",
                    "account": account,
                    "secret": secret,
                    "project": project,
                    "enterprise": enterprise
                }
            }
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get('code') == '201' and 'access_token' in result:
                return result['access_token']
            else:
                self.stdout.write(self.style.ERROR(f'Token响应: {result}'))
                return None

        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'获取token失败: {e}'))
            return None

    def _fetch_persons_page(self, token, project_id, tenant_id, page_size, cur_page, last_sync_time=None):
        """获取一页人员数据"""
        url = f'https://apig.hieds.net/api/meta/api/engine/idata/projects/{project_id}/catalog/hr_person_info'
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }

        data = {
            "tenant_id": tenant_id,
            "pageSize": page_size,
            "curPage": cur_page,
        }

        # 如果有增量同步时间，添加到查询参数
        if last_sync_time:
            data["startTime"] = last_sync_time.strftime('%Y-%m-%d %H:%M:%S')

        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 200:
                return result.get('data', {})
            else:
                self.stdout.write(self.style.ERROR(f'API响应错误: {result}'))
                return None

        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'获取人员数据失败: {e}'))
            return None

    def _save_persons(self, persons):
        """保存人员数据"""
        synced_count = 0

        for person_data in persons:
            try:
                person_id = person_data['personId']

                # 准备数据映射
                person_dict = {
                    'person_id': person_id,
                    'employee_number': person_data.get('employeeNumber', ''),
                    'full_name': person_data.get('fullName', ''),
                    'english_name': person_data.get('englishName'),
                    'sex': person_data.get('sex'),
                    'birth_day': self._parse_date(person_data.get('birthDay')),
                    'nationality_code': person_data.get('nationalityCode'),
                    'person_type': person_data.get('personType', ''),
                    'employee_status': person_data.get('employeeStatus', ''),
                    'employee_account': person_data.get('employeeAccount'),
                    'user_id': person_data.get('userId'),
                    'employee_description': person_data.get('employeeDescription'),
                    'email_address': person_data.get('emailAddress'),
                    'telephone_number1': person_data.get('telephoneNumber1'),
                    'telephone_number2': person_data.get('telephoneNumber2'),
                    'telephone_number3': person_data.get('telephoneNumber3'),
                    'full_address': person_data.get('fullAddress'),
                    'postal_code': person_data.get('postalCode'),
                    'base_location': person_data.get('baseLocation'),
                    'expense_account': person_data.get('expenseAccount'),
                    'person_pinyin_name': person_data.get('personPinyinName'),
                    'original_hire_date': self._parse_date(person_data.get('originalHireDate')),
                    'creation_date': self._parse_datetime(person_data.get('creationDate')),
                    'last_update_date': self._parse_datetime(person_data.get('lastUpdateDate')),
                    'effective_date': self._parse_date(person_data.get('effectiveDate')),
                    'disable_date': self._parse_date(person_data.get('disableDate')),
                    'person_dept': person_data.get('personDept', []),
                    'tenant_id': person_data.get('tenantId', ''),
                    'created_by': person_data.get('createdBy', ''),
                    'last_updated_by': person_data.get('lastUpdatedBy', ''),
                }

                # 使用update_or_create根据person_id更新或创建记录
                person, created = HrPerson.objects.update_or_create(
                    person_id=person_id,
                    defaults=person_dict
                )

                synced_count += 1
                if created:
                    self.stdout.write(f'新增人员: {person.employee_number} - {person.full_name}')
                    # 为新人员创建默认账号记录
                    accounts_created = HrPersonAccount.create_default_accounts(person)
                    self.stdout.write(f'  创建账号记录: {len(accounts_created)} 个')
                else:
                    self.stdout.write(f'更新人员: {person.employee_number} - {person.full_name}')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'保存人员数据失败: {person_data.get("personId", "unknown")}, 错误: {e}'))
                continue

        return synced_count

    def _parse_date(self, date_str):
        """解析日期字符串"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None

    def _parse_datetime(self, datetime_str):
        """解析日期时间字符串"""
        if not datetime_str:
            return timezone.now()  # 默认当前时间
        try:
            # 处理不同的时间格式
            if 'T' in datetime_str:
                return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            else:
                return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return timezone.now()