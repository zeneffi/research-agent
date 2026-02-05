"""
message_generator.py のテスト
"""
from scripts.lib.message_generator import detect_company_type, generate_sales_message


def test_detect_startup():
    """スタートアップ判定のテスト"""
    company = {
        'company_name': 'テストスタートアップ',
        'custom_field_1': 'シリーズAで資金調達',
        'custom_field_2': '5億円',
        'custom_field_3': '2024年1月'
    }
    assert detect_company_type(company) == 'startup'


def test_detect_it_company():
    """IT企業判定のテスト"""
    company = {
        'company_name': 'テストIT企業',
        'custom_field_1': 'React, Python, AWS',
        'custom_field_2': '100名',
        'custom_field_3': ''
    }
    assert detect_company_type(company) == 'it_company'


def test_detect_manufacturing():
    """製造業判定のテスト"""
    company = {
        'company_name': 'テスト製造業',
        'custom_field_1': '自動車部品',
        'custom_field_2': '栃木県',
        'custom_field_3': 'ISO 9001'
    }
    assert detect_company_type(company) == 'manufacturing'


def test_detect_general():
    """汎用判定のテスト"""
    company = {
        'company_name': 'テスト企業',
        'custom_field_1': '',
        'custom_field_2': '',
        'custom_field_3': ''
    }
    assert detect_company_type(company) == 'general'


def test_generate_sales_message_startup():
    """スタートアップ向けメッセージ生成のテスト"""
    company = {
        'company_name': 'テストスタートアップ',
        'custom_field_1': 'シリーズA',
        'custom_field_2': '5億円',
        'custom_field_3': '2024年1月',
        'business': 'SaaS事業'
    }
    sender = {
        'company_name': '株式会社Example',
        'contact_name': '山田太郎'
    }

    message = generate_sales_message(company, sender)

    assert 'シリーズA' in message
    assert '5億円' in message
    assert '調達' in message
    assert len(message) > 100  # 最低限の長さチェック


def test_generate_sales_message_it():
    """IT企業向けメッセージ生成のテスト"""
    company = {
        'company_name': 'テストIT企業',
        'custom_field_1': 'React, Python',
        'custom_field_2': '100名',
        'custom_field_3': '',
        'business': 'Web開発'
    }
    sender = {
        'company_name': '株式会社Example',
        'contact_name': '山田太郎'
    }

    message = generate_sales_message(company, sender)

    assert 'React, Python' in message
    assert 'Web開発' in message
    assert len(message) > 100
