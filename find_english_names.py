#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文影视剧英文名查找工具
主要基于TMDB和豆瓣两个权威数据库搜索中文电视剧/电影的英文名称
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys
import os
from urllib.parse import quote
import csv
from datetime import datetime
import textwrap

# ==================== 配置 ====================
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'Referer': 'https://www.google.com/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

# 创建session以保持cookies
session = requests.Session()
session.headers.update(HEADERS)

# ==================== 搜索函数 ====================

def has_chinese(text):
    """检查文本是否包含中文字符"""
    if not text:
        return False
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def search_tmdb(name):
    """在 TMDB 上搜索（最可靠）"""
    try:
        # 提取季节信息用于更精准的搜索
        clean_name, season_info = extract_season_info(name)
        
        # 构建搜索变体
        search_variants = [name]
        if clean_name != name:
            search_variants.append(clean_name)
        
        # 如果有季节信息，添加季节变体
        if season_info['has_season'] and season_info['season_number']:
            season_variants = [
                f"{clean_name} {season_info['season_number']}",
                f"{clean_name} season {season_info['season_number']}",
                f"{clean_name} s{season_info['season_number']}",
            ]
            search_variants.extend(season_variants)
        
        all_results = []
        
        # 使用所有搜索变体进行搜索
        for search_variant in search_variants:
            search_url = f"https://www.themoviedb.org/search?query={quote(search_variant)}"
            response = session.get(search_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 查找TV和Movie结果
            for media_type in ['tv', 'movie']:
                links = soup.find_all('a', href=re.compile(f'/{media_type}/\\d+'))
                for link in links[:10]:  # 增加搜索范围
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    if href and not href.startswith('http'):
                        href = 'https://www.themoviedb.org' + href
                    # 跳过空标题
                    if not title or title.strip() == '':
                        continue
                    if title and title not in [r['full_title'] for r in results] and title not in [r['full_title'] for r in all_results]:
                        # 方法1: 提取英文名（去掉中文括号内容）
                        english_title = re.sub(r'\([^)]*[\u4e00-\u9fff][^)]*\)', '', title).strip()
                        # 方法2: 如果格式是"英文名(中文名)"，提取英文名
                        if has_chinese(english_title):
                            match = re.match(r'^([A-Za-z][^(\u4e00-\u9fff]*)', english_title)
                            if match:
                                english_title = match.group(1).strip()
                        # 方法3: 如果格式是"中文名 / 英文名"，提取英文名
                        if has_chinese(english_title):
                            match = re.search(r'[\u4e00-\u9fff]+[^/]*/\s*([A-Za-z][^/\n(]+)', title)
                            if match:
                                english_title = match.group(1).strip()
                        # 方法4: 如果格式是"中文名 (英文名)"，提取英文名
                        if has_chinese(english_title):
                            match = re.search(r'[\u4e00-\u9fff]+\s*\(([A-Za-z][^)]+)\)', title)
                            if match:
                                english_title = match.group(1).strip()
                        
                        # 如果提取后仍包含中文，尝试从URL提取
                        if has_chinese(english_title) and href:
                            # 从URL中提取英文名（TMDB URL通常包含英文名）
                            url_match = re.search(r'/(?:tv|movie)/\d+-(.+?)(?:\?|$)', href)
                            if url_match:
                                url_title = url_match.group(1).replace('-', ' ').title()
                                if not has_chinese(url_title):
                                    english_title = url_title
                        
                        # 如果还是没有英文名，使用原标题
                        if not english_title:
                            english_title = title
                        
                        # 计算匹配分数（考虑季节匹配）
                        score = 0
                        title_lower = title.lower()
                        search_variant_lower = search_variant.lower()
                        
                        # 基础匹配分数
                        if search_variant_lower in title_lower:
                            score += 10
                        
                        # 季节匹配加分
                        if season_info['has_season'] and season_info['season_number']:
                            season_patterns = [
                                rf'season\s*{season_info["season_number"]}',
                                rf's\s*{season_info["season_number"]}',
                                rf'\b{season_info["season_number"]}\b',
                            ]
                            for pattern in season_patterns:
                                if re.search(pattern, title_lower):
                                    score += 15  # 季节匹配高分
                                    break
                        
                        results.append({
                            'title': english_title,
                            'full_title': title,
                            'link': href,
                            'type': media_type,
                            'source': 'TMDB',
                            'has_chinese': has_chinese(english_title),
                            'score': score,
                            'search_variant': search_variant
                        })
            
            all_results.extend(results)
            
            # 如果已经找到高匹配度的结果，停止搜索其他变体
            high_score_results = [r for r in results if r['score'] >= 15]
            if high_score_results:
                break
        
        # 按分数排序，优先返回高匹配度的结果
        if all_results:
            all_results.sort(key=lambda x: x['score'], reverse=True)
            
            # 优先返回高匹配度（包含季节匹配）的结果
            high_score_results = [r for r in all_results if r['score'] >= 15]
            if high_score_results:
                best_result = high_score_results[0]
                # 清理临时字段
                best_result.pop('score', None)
                best_result.pop('has_chinese', None)
                best_result.pop('search_variant', None)
                return best_result
            
            # 如果没有高匹配度的，使用原有的评分逻辑
            # 计算每个结果的匹配分数（原有逻辑）
            for result in all_results:
                score = result.get('score', 0)  # 保留已有的基础分数
                title_lower = result['title'].lower()
                full_title_lower = result['full_title'].lower()
                name_lower = name.lower()
                
                # 不包含中文 +10分
                if not result['has_chinese']:
                    score += 10
                # 标题包含搜索关键词 +5分
                if name_lower in title_lower or name_lower in full_title_lower:
                    score += 5
                # 是movie类型 +2分（电影通常更准确）
                if result['type'] == 'movie':
                    score += 2
                
                result['score'] = score
            
            # 按分数排序
            all_results.sort(key=lambda x: x['score'], reverse=True)
            
            # 优先返回不包含中文的结果
            for result in all_results:
                if not result['has_chinese']:
                    # 清理临时字段
                    result.pop('score', None)
                    result.pop('has_chinese', None)
                    result.pop('search_variant', None)
                    return result
            
            # 如果没有纯英文的，但找到了中文结果，返回第一个结果
            best_result = all_results[0]
            best_result.pop('score', None)
            best_result.pop('has_chinese', None)
            best_result.pop('search_variant', None)
            
            # 结果包含中文，显示"无"作为英文标题，添加平台备注
            if has_chinese(best_result['title']):
                best_result['title'] = '无'  # 英文标题显示为"无"
                best_result['note'] = 'TMDB：只有中文名，无英文名'
            
            return best_result
        
        return None
        
    except Exception as e:
        return None

def extract_season_info(name):
    """提取季节信息，返回 (clean_name, season_info)"""
    season_info = {
        'has_season': False,
        'season_number': None,
        'season_text': None,
        'year': None
    }
    
    # 提取年份
    year_match = re.search(r'\b(19|20)\d{2}\b', name)
    if year_match:
        season_info['year'] = year_match.group(0)
    
    # 检测季节标识
    # 匹配模式：第X季、第X部、X、第二季、第二部、Season X、S0X、S X等
    season_patterns = [
        (r'第\s*(\d+)\s*季', '第{}季'),
        (r'第\s*(\d+)\s*部', '第{}部'),
        (r'第\s*([一二三四五六七八九十]+)\s*季', '第{}季'),
        (r'第\s*([一二三四五六七八九十]+)\s*部', '第{}部'),
        (r'\b([一二三四五六七八九十]+)\s*季', '{}季'),
        (r'\b([一二三四五六七八九十]+)\s*部', '{}部'),
        (r'Season\s*(\d+)', 'Season {}'),
        (r'S\s*(\d+)', 'S{}'),
        (r'\b(\d+)\s*季', '{}季'),
        (r'\b(\d+)\s*部', '{}部'),
        (r'(\d+)$', '{}'),  # 末尾数字，如"大江大河2"
        (r'(\d+)\s*$', '{}'),  # 末尾数字带空格
    ]
    
    for pattern, format_str in season_patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            season_num = match.group(1)
            # 转换中文数字
            if season_num in ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']:
                chinese_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, 
                               '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
                season_info['season_number'] = chinese_nums.get(season_num, 1)
                season_info['season_text'] = format_str.format(season_num)
            else:
                season_info['season_number'] = int(season_num)
                season_info['season_text'] = format_str.format(season_num)
            season_info['has_season'] = True
            break
    
    # 清理搜索关键词
    clean_name = name
    # 先移除季节标识
    for pattern, _ in season_patterns:
        clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
    # 再移除年份
    clean_name = re.sub(r'\s*\b(19|20)\d{2}\b\s*年?\s*', '', clean_name)
    clean_name = re.sub(r'[《》]', '', clean_name)  # 移除书名号
    clean_name = clean_name.strip()
    
    # 如果清理后为空，使用原名称（不含季节和年份信息）
    if not clean_name:
        clean_name = re.sub(r'[《》]', '', name)
        clean_name = re.sub(r'\s*\b(19|20)\d{2}\b\s*年?\s*', '', clean_name)
        # 对于末尾数字的情况，保留基础名称
        clean_name = re.sub(r'\d+$', '', clean_name)
        clean_name = clean_name.strip() or re.sub(r'[《》\d]', '', name).strip() or name
    
    return clean_name, season_info

def search_douban(name):
    """在豆瓣上搜索（中文影视数据库）- 使用多种方法"""
    detail_url = None
    chinese_title_only = None  # 记录只有中文名的情况
    search_results = []  # 存储搜索结果用于备用
    
    # 方法0: 预处理 - 提取季节信息和清理搜索关键词
    clean_name, season_info = extract_season_info(name)
    
    # 构建季节相关的搜索变体
    search_variants = [name, clean_name]
    if season_info['has_season'] and season_info['season_number']:
        # 添加季节变体
        season_variants = [
            f"{clean_name} 第{season_info['season_number']}季",
            f"{clean_name}{season_info['season_number']}",
            f"{clean_name} ({season_info['season_number']})",
        ]
        # 如果季节文本存在，也加入
        if season_info['season_text']:
            season_variants.append(f"{clean_name} {season_info['season_text']}")
        
        search_variants.extend(season_variants)
    
    # 方法1: 尝试移动版搜索（可能更简单）
    try:
        # 使用所有搜索变体进行搜索
        for search_variant in search_variants:
            mobile_url = f"https://m.douban.com/search/?query={quote(search_variant)}"
            # 使用移动版headers
            mobile_session = requests.Session()
            mobile_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            })
            response = mobile_session.get(mobile_url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # 查找所有subject链接（包括/movie/subject/和/subject/格式）
                links = soup.find_all('a', href=re.compile(r'(?:/movie)?/subject/\d+'))
                if links:
                    # 为每个链接计算匹配分数（考虑季节匹配）
                    for link in links:
                        link_text = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        # 计算匹配分数
                        score = 0
                        # 基础匹配分数
                        for variant in search_variants:
                            if variant in link_text:
                                score += 10
                                break
                        
                        # 季节匹配加分
                        if season_info['has_season'] and season_info['season_number']:
                            # 检查链接文本是否包含季节信息
                            season_patterns = [
                                rf'第\s*{season_info["season_number"]}\s*季',
                                rf'{season_info["season_number"]}\s*季',
                                rf'Season\s*{season_info["season_number"]}',
                                rf'S\s*{season_info["season_number"]}',
                            ]
                            for pattern in season_patterns:
                                if re.search(pattern, link_text, re.IGNORECASE):
                                    score += 20  # 季节匹配高分
                                    break
                        
                        if '/movie/subject/' in href:
                            score += 5  # movie类型优先
                        if len(link_text) > 2:  # 避免太短的匹配
                            score += 2
                        
                        if score > 0:
                            search_results.append((score, link_text, href))
                    
                    # 按分数排序
                    search_results.sort(key=lambda x: x[0], reverse=True)
                    
                    # 使用最高分的链接
                    if search_results:
                        best_result = search_results[0]
                        href = best_result[2]
                        match = re.search(r'/subject/(\d+)', href)
                        if match:
                            subject_id = match.group(1)
                            detail_url = f'https://movie.douban.com/subject/{subject_id}/'
                            break  # 找到有效链接就停止搜索
    except Exception as e:
        pass
    
    # 方法2: 尝试网页搜索（增强版）
    if not detail_url:
        try:
            # 使用所有搜索变体
            all_search_variants = list(set(search_variants))  # 去重
            
            search_urls = []
            for variant in all_search_variants:
                if variant:
                    search_urls.extend([
                        f"https://www.douban.com/search?q={quote(variant)}&cat=1002",
                        f"https://www.douban.com/search?q={quote(variant)}",
                    ])
            
            for search_url in search_urls:
                try:
                    response = session.get(search_url, timeout=15, allow_redirects=True)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 查找所有链接
                    all_links = soup.find_all('a', href=True)
                    candidate_links = []
                    
                    for link in all_links:
                        href = link.get('href', '')
                        link_text = link.get_text(strip=True)
                        
                        # 检查是否是有效的subject链接
                        if '/subject/' in href and re.search(r'/subject/\d+', href):
                            score = 0
                            # 文本匹配分数（考虑季节匹配）
                            for variant in all_search_variants:
                                if variant and variant in link_text:
                                    score += 10
                                    break
                            
                            # 季节匹配加分
                            if season_info['has_season'] and season_info['season_number']:
                                season_patterns = [
                                    rf'第\s*{season_info["season_number"]}\s*季',
                                    rf'{season_info["season_number"]}\s*季',
                                    rf'Season\s*{season_info["season_number"]}',
                                    rf'S\s*{season_info["season_number"]}',
                                ]
                                for pattern in season_patterns:
                                    if re.search(pattern, link_text, re.IGNORECASE):
                                        score += 20  # 季节匹配高分
                                        break
                            
                            # 父元素匹配
                            parent = link.parent
                            if parent:
                                parent_text = parent.get_text()
                                for variant in all_search_variants:
                                    if variant and variant in parent_text:
                                        score += 5
                                        break
                            # 兄弟元素匹配
                            for sibling in [link.previous_sibling, link.next_sibling]:
                                if sibling:
                                    sibling_text = str(sibling)
                                    for variant in all_search_variants:
                                        if variant and variant in sibling_text:
                                            score += 3
                                            break
                            
                            # URL质量分数
                            if '/movie/subject/' in href:
                                score += 2
                            
                            if score > 0:
                                candidate_links.append((score, href))
                    
                    if candidate_links:
                        candidate_links.sort(key=lambda x: x[0], reverse=True)
                        detail_url = candidate_links[0][1]
                        if not detail_url.startswith('http'):
                            detail_url = 'https://www.douban.com' + detail_url
                        break
                    
                    # 备用：查找第一个subject链接
                    if not detail_url:
                        for link in all_links:
                            href = link.get('href', '')
                            if '/subject/' in href and re.search(r'/subject/\d+', href):
                                detail_url = href
                                if not detail_url.startswith('http'):
                                    detail_url = 'https://www.douban.com' + detail_url
                                break
                    
                    if detail_url:
                        break
                except:
                    continue
        except:
            pass
    
    # 方法3: 尝试使用备用搜索（如果仍然没有找到）
    if not detail_url and search_results:
        # 使用移动版搜索的备用结果
        for result in search_results[1:4]:  # 尝试前3个备用结果
            href = result[2]
            match = re.search(r'/subject/(\d+)', href)
            if match:
                subject_id = match.group(1)
                detail_url = f'https://movie.douban.com/subject/{subject_id}/'
                break
    
    if not detail_url:
        return None
    
    # 访问详情页获取英文名（增强版）
    try:
        # 使用桌面版headers访问详情页
        detail_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.douban.com/',
        }
        # 使用新的session访问详情页
        detail_session = requests.Session()
        detail_session.headers.update(detail_headers)
        detail_response = detail_session.get(detail_url, timeout=15, allow_redirects=True)
        detail_response.raise_for_status()
        detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
        
        # 方法1: 从span标签获取（豆瓣最常用格式）- 增强版
        spans = detail_soup.find_all('span', {'property': 'v:itemreviewed'})
        for span in spans:
            span_text = span.get_text(strip=True)
            # 匹配格式：中文名 / 英文名 或 中文名(英文名) 或 中文名 英文名
            patterns = [
                r'[\u4e00-\u9fff]+[^/]*/\s*([A-Za-z][^/\n(]+)',  # 中文名 / 英文名
                r'[\u4e00-\u9fff]+\s*\(([A-Za-z][^)]+)\)',  # 中文名(英文名)
                r'[\u4e00-\u9fff]+[：:]\s*([A-Za-z][A-Za-z\s:,\'\-\.0-9]+)',  # 中文名：英文名
                r'[\u4e00-\u9fff]+\s+([A-Za-z][A-Za-z\s:,\'\-\.0-9]+)',  # 中文名 英文名
                r'([A-Za-z][A-Za-z\s:,\'\-\.0-9]+)\s*[\u4e00-\u9fff]+',  # 英文名 中文名（反向）
                r'([A-Za-z][A-Za-z\s:,\'\-\.0-9]+)\s*/\s*[\u4e00-\u9fff]+',  # 英文名 / 中文名
            ]
            for pattern in patterns:
                match = re.search(pattern, span_text)
                if match:
                    english_title = match.group(1).strip()
                    # 清理可能的年份、评分等
                    english_title = re.sub(r'\s*\(.*?\)\s*$', '', english_title).strip()
                    english_title = re.sub(r'\s*-\s*豆瓣$', '', english_title).strip()
                    english_title = re.sub(r'\s*\d+\.\d+\s*$', '', english_title).strip()  # 移除评分
                    if english_title and len(english_title) > 1 and not has_chinese(english_title):
                        return {
                            'title': english_title,
                            'full_title': span_text,
                            'link': detail_response.url,
                            'source': 'Douban'
                        }
        
        # 方法1.5: 从info区域查找"又名"字段（专门针对豆瓣页面结构优化）
        info_div = detail_soup.find('div', id='info')
        if info_div:
            # 豆瓣页面结构：查找包含"又名"的span标签（class为"pl"）
            for span in info_div.find_all('span', class_='pl'):
                span_text = span.get_text(strip=True)
                if '又名' in span_text:
                    # 获取紧邻的文本内容（next_sibling）
                    alt_names_text = ''
                    next_node = span.next_sibling
                    if next_node:
                        if isinstance(next_node, str):
                            alt_names_text = next_node.strip()
                        elif hasattr(next_node, 'get_text'):
                            alt_names_text = next_node.get_text(strip=True)
                    
                    # 如果直接获取不到，尝试获取下一个兄弟节点的文本
                    if not alt_names_text:
                        next_element = span.find_next_sibling()
                        if next_element:
                            alt_names_text = next_element.get_text(strip=True)
                    
                    # 处理多个名称（用/分隔）
                    if alt_names_text:
                        # 分割多个名称（支持多种分隔符）
                        alt_names = [n.strip() for n in re.split(r'[/|，,；;、]', alt_names_text)]
                        
                        # 优先选择包含更多英文单词的标题
                        best_english_name = None
                        best_score = 0
                        
                        for alt_name in alt_names:
                            if (alt_name and 
                                len(alt_name) > 3 and
                                alt_name.lower() not in ['又名', '片名', 'imdb', 'tmdb'] and
                                not has_chinese(alt_name)):  # 检查是否包含中文字符
                                
                                # 计算英文名字的质量分数
                                score = 0
                                # 长度分数
                                score += len(alt_name) * 0.1
                                # 包含空格（多个单词）加分
                                if ' ' in alt_name:
                                    score += 5
                                # 包含常见英文单词加分
                                common_words = ['the', 'of', 'and', 'in', 'to', 'a', 'is', 'for', 'on', 'with']
                                alt_lower = alt_name.lower()
                                for word in common_words:
                                    if word in alt_lower:
                                        score += 2
                                # 包含数字（如年份）加分
                                if re.search(r'\d+', alt_name):
                                    score += 3
                                
                                if score > best_score:
                                    best_score = score
                                    best_english_name = alt_name
                        
                        # 返回最好的英文名
                        if best_english_name:
                            result = {
                                'title': best_english_name.strip(),
                                'full_title': alt_names_text.strip(),
                                'link': detail_response.url,
                                'source': 'Douban'
                            }
                            
                            # 如果找到了IMDb链接，也一并返回
                            imdb_link = detail_soup.find('a', href=re.compile(r'imdb\.com'))
                            if imdb_link:
                                result['imdb_link'] = imdb_link.get('href', '')
                            
                            return result
        
        # 方法2: 从h1标题获取（增强版）
        h1_tag = detail_soup.find('h1')
        if h1_tag:
            h1_text = h1_tag.get_text(strip=True)
            patterns = [
                r'[\u4e00-\u9fff]+[^/]*/\s*([A-Za-z][^/\n(]+)',  # 中文名 / 英文名
                r'[\u4e00-\u9fff]+\s*\(([A-Za-z][^)]+)\)',  # 中文名(英文名)
                r'[\u4e00-\u9fff]+[：:]\s*([A-Za-z][^/\n(]+)',  # 中文名：英文名
                r'([A-Za-z][A-Za-z\s:,\'\-\.0-9]+)\s*[\u4e00-\u9fff]+',  # 英文名 中文名
            ]
            for pattern in patterns:
                match = re.search(pattern, h1_text)
                if match:
                    english_title = match.group(1).strip()
                    english_title = re.sub(r'\s*\(.*?\)\s*$', '', english_title).strip()
                    if english_title and len(english_title) > 1 and not has_chinese(english_title):
                        return {
                            'title': english_title,
                            'full_title': h1_text,
                            'link': detail_response.url,
                            'source': 'Douban'
                        }
        
        # 方法3: 从页面标题获取（增强版）
        title_tag = detail_soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            patterns = [
                r'[\u4e00-\u9fff]+[^/]*/\s*([A-Za-z][^/\n(]+)',
                r'[\u4e00-\u9fff]+\s*\(([A-Za-z][^)]+)\)',
                r'([A-Za-z][A-Za-z\s:,\'\-\.0-9]+)\s*[\u4e00-\u9fff]+',
            ]
            for pattern in patterns:
                match = re.search(pattern, title_text)
                if match:
                    english_title = match.group(1).strip()
                    english_title = re.sub(r'\s*\(.*?\)\s*$', '', english_title).strip()
                    english_title = re.sub(r'\s*-\s*豆瓣$', '', english_title).strip()
                    if english_title and len(english_title) > 1 and not has_chinese(english_title):
                        return {
                            'title': english_title,
                            'full_title': title_text,
                            'link': detail_response.url,
                            'source': 'Douban'
                        }
        
        # 方法4: 从其他元数据获取
        # 查找meta标签
        meta_tags = detail_soup.find_all('meta', attrs={'name': True})
        for meta in meta_tags:
            meta_name = meta.get('name', '').lower()
            meta_content = meta.get('content', '')
            if 'title' in meta_name and meta_content:
                # 尝试从meta内容提取英文名
                patterns = [
                    r'[\u4e00-\u9fff]+[^/]*/\s*([A-Za-z][^/\n(]+)',
                    r'[\u4e00-\u9fff]+\s*\(([A-Za-z][^)]+)\)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, meta_content)
                    if match:
                        english_title = match.group(1).strip()
                        if english_title and len(english_title) > 1 and not has_chinese(english_title):
                            return {
                                'title': english_title,
                                'full_title': meta_content,
                                'link': detail_response.url,
                                'source': 'Douban'
                            }
        
        # 方法5: 如果找不到英文名，记录只有中文名的情况（增强版）
        # 获取页面中的中文标题
        h1_tag = detail_soup.find('h1')
        if h1_tag:
            h1_text = h1_tag.get_text(strip=True)
            # 提取纯中文标题（去除英文和其他字符）
            chinese_match = re.search(r'^[\u4e00-\u9fff\s·]+', h1_text)  # 包含间隔号
            if chinese_match:
                chinese_title = chinese_match.group(0).strip()
                if chinese_title and len(chinese_title) >= 2:
                    chinese_title_only = {
                        'title': '无',  # 英文标题显示为"无"
                        'chinese_title': chinese_title,  # 保存中文标题
                        'full_title': h1_text,
                        'link': detail_response.url,
                        'source': 'Douban',
                        'has_english': False,  # 标记没有英文名
                        'note': '豆瓣：只有中文名，无英文名'
                    }
        
        # 方法6: 从span标签获取中文标题（备用）
        if not chinese_title_only:
            spans = detail_soup.find_all('span', {'property': 'v:itemreviewed'})
            for span in spans:
                span_text = span.get_text(strip=True)
                chinese_match = re.search(r'^[\u4e00-\u9fff\s·]+', span_text)
                if chinese_match:
                    chinese_title = chinese_match.group(0).strip()
                    if chinese_title and len(chinese_title) >= 2:
                        chinese_title_only = {
                            'title': '无',  # 英文标题显示为"无"
                            'chinese_title': chinese_title,  # 保存中文标题
                            'full_title': span_text,
                            'link': detail_response.url,
                            'source': 'Douban',
                            'has_english': False,
                            'note': '豆瓣：只有中文名，无英文名'
                        }
                        break
        
        # 方法7: 从页面内容获取年份和类型信息（用于更好的标注）
        year_info = None
        type_info = None
        
        # 获取年份
        year_span = detail_soup.find('span', class_='year')
        if year_span:
            year_text = year_span.get_text(strip=True)
            year_match = re.search(r'\d{4}', year_text)
            if year_match:
                year_info = year_match.group(0)
        
        # 获取类型
        type_span = detail_soup.find('span', {'property': 'v:genre'})
        if type_span:
            type_info = type_span.get_text(strip=True)
        
        # 更新中文标题的注释信息
        if chinese_title_only and (year_info or type_info):
            note_parts = ['豆瓣：只有中文名，无英文名']
            if year_info:
                note_parts.append(f"年份：{year_info}")
            if type_info:
                note_parts.append(f"类型：{type_info}")
            chinese_title_only['note'] = ' | '.join(note_parts)
    
    except Exception as e:
        # 如果访问详情页失败，返回None
        pass
    
    # 如果找到了页面但只有中文名，返回中文名信息
    if chinese_title_only:
        return chinese_title_only
    
    return None


def search_all_sources(name):
    """在所有数据源中搜索（主要基于TMDB和豆瓣）"""
    results = {
        'chinese_name': name,
        'tmdb': None,
        'douban': None,
    }
    
    # 按优先级搜索
    print(f"  搜索 TMDB...", end='', flush=True)
    results['tmdb'] = search_tmdb(name)
    print(" ✓" if results['tmdb'] else " ✗")
    time.sleep(1.5)
    
    print(f"  搜索 豆瓣...", end='', flush=True)
    results['douban'] = search_douban(name)
    print(" ✓" if results['douban'] else " ✗")
    time.sleep(1.5)

    # 结果后处理：季节严格校验，避免TMDB误匹配
    try:
        clean_name, season_info = extract_season_info(name)
        if season_info['has_season'] and season_info['season_number'] and results['tmdb']:
            tmdb = results['tmdb']
            title_lower = (tmdb.get('title') or '').lower()
            full_title_lower = (tmdb.get('full_title') or '').lower()
            link_lower = (tmdb.get('link') or '').lower()
            season_num = str(season_info['season_number'])

            # 必须是剧集类型并且包含季节痕迹
            has_season_marker = (
                re.search(rf"season\s*{season_num}", full_title_lower) or
                re.search(rf"\bs\s*{season_num}\b", full_title_lower) or
                re.search(rf"\b{season_num}\b", full_title_lower) or
                re.search(rf"season-{season_num}", link_lower)
            )

            is_tv = (tmdb.get('type') == 'tv')

            # 如果不是TV类型，或没有任何季节标记，则认为TMDB不匹配，置空
            if (not is_tv) or (not has_season_marker):
                results['tmdb'] = None
    except Exception:
        pass
    
    return results

# ==================== 文件处理 ====================

def load_names_from_file(filepath):
    """从文件加载剧名列表（支持txt和csv）"""
    names = []
    try:
        if filepath.endswith('.csv'):
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        names.append(row[0].strip())
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        names.append(line)
    except Exception as e:
        print(f"错误: 无法读取文件 {filepath}: {e}")
    return names

def format_text_for_excel(text, max_width=50):
    """格式化文本以便在Excel中更好地显示，支持自动换行"""
    if not text:
        return ''
    
    # 对长文本进行换行处理
    if len(text) > max_width:
        # 使用textwrap进行智能换行
        wrapped_lines = textwrap.wrap(text, width=max_width, break_long_words=False)
        # 使用Excel支持的换行符
        return '\n'.join(wrapped_lines)
    
    return text

def save_results_to_csv(results, output_file):
    """保存结果到CSV文件（主要基于TMDB和豆瓣）- 增强版，支持Excel格式优化"""
    
    # 首先分析数据以确定最佳列宽
    max_lengths = {
        'chinese_name': 10,  # 最小宽度
        'tmdb_title': 15,
        'tmdb_link': 30,
        'douban_title': 15,
        'douban_link': 30,
        'best_match': 15
    }
    
    # 分析所有数据以确定最大长度
    for result in results:
        # 中文名称长度
        max_lengths['chinese_name'] = max(max_lengths['chinese_name'], len(result['chinese_name']))
        
        # TMDB数据长度
        if result['tmdb']:
            max_lengths['tmdb_title'] = max(max_lengths['tmdb_title'], len(result['tmdb'].get('title', '')))
            max_lengths['tmdb_link'] = max(max_lengths['tmdb_link'], len(result['tmdb'].get('link', '')))
        
        # 豆瓣数据长度
        if result['douban']:
            max_lengths['douban_title'] = max(max_lengths['douban_title'], len(result['douban'].get('title', '')))
            max_lengths['douban_link'] = max(max_lengths['douban_link'], len(result['douban'].get('link', '')))
        
        # 最佳匹配长度
        best_match = ''
        if result['tmdb']:
            best_match = result['tmdb'].get('title', '')
        elif result['douban']:
            best_match = result['douban'].get('title', '')
        max_lengths['best_match'] = max(max_lengths['best_match'], len(best_match))
    
    # 设置最大列宽限制，避免过宽
    for key in max_lengths:
        max_lengths[key] = min(max_lengths[key], 80)  # 最大80字符
    
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:  # utf-8-sig for Excel compatibility
        writer = csv.writer(f)
        
        # 写入标题行（统一显示格式）
        headers = [
            '中文名称', 
            'TMDB英文名称', 'TMDB链接', 
            '豆瓣英文名称', '豆瓣链接',
            '最佳匹配（推荐）'
        ]
        writer.writerow(headers)
        
        # 写入数据行
        for result in results:
            row = []
            
            # 中文名称 - 格式化
            chinese_name = format_text_for_excel(result['chinese_name'], max_lengths['chinese_name'])
            row.append(chinese_name)
            
            # TMDB - 格式化标题和链接
            if result['tmdb']:
                tmdb_title = format_text_for_excel(result['tmdb'].get('title', ''), max_lengths['tmdb_title'])
                tmdb_link = format_text_for_excel(result['tmdb'].get('link', ''), max_lengths['tmdb_link'])
                row.extend([tmdb_title, tmdb_link])
            else:
                row.extend(['无', '无'])
            
            # 豆瓣 - 格式化标题和链接
            if result['douban']:
                # 检查是否有英文名
                has_english = result['douban'].get('has_english', True)
                if has_english:
                    douban_title = format_text_for_excel(result['douban'].get('title', ''), max_lengths['douban_title'])
                else:
                    douban_title = '无'  # 只有中文名时显示"无"
                douban_link = format_text_for_excel(result['douban'].get('link', ''), max_lengths['douban_link'])
                row.extend([douban_title, douban_link])
            else:
                row.extend(['无', '无'])
            
            # 最佳匹配（TMDB始终优先，只有TMDB没有结果时才使用豆瓣）- 格式化
            best_match = ''
            if result['tmdb']:
                best_match = result['tmdb'].get('title', '')
            elif result['douban']:
                has_english = result['douban'].get('has_english', True)
                if has_english:
                    best_match = result['douban'].get('title', '')
                else:
                    best_match = '无'  # 只有中文名时显示"无"
            best_match_formatted = format_text_for_excel(best_match, max_lengths['best_match'])
            row.append(best_match_formatted)
            
            writer.writerow(row)
    
    # 生成Excel格式说明文件
    readme_file = output_file.replace('.csv', '_excel格式说明.txt')
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write("""CSV文件Excel格式优化说明

本CSV文件已针对Excel进行以下优化：

1. 自动换行：
   - 长文本已自动换行处理，在Excel中会自动换行显示
   - 建议设置：选中所有单元格 → 开始 → 自动换行

2. 最优列宽：
   - 根据内容长度自动调整列宽
   - 建议设置：选中所有列 → 开始 → 格式 → 自动调整列宽

3. 最优行高：
   - 根据内容自动调整行高
   - 建议设置：选中所有行 → 开始 → 格式 → 自动调整行高

4. 编码优化：
   - 使用UTF-8 with BOM编码，确保中文正常显示
   - 在Excel中直接打开即可正确显示中文

5. 链接处理：
   - URL链接已优化格式，便于点击访问
   - 长URL已适当换行，不影响显示效果

使用建议：
- 在Excel中打开后，建议全选并启用"自动换行"
- 根据需要调整字体大小（推荐10-12号字体）
- 可设置交替行背景色提高可读性
""")
    
    return readme_file

def save_results_to_json(results, output_file):
    """保存结果到JSON文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

# ==================== 主程序 ====================

def main():
    """主函数"""
    print("=" * 60)
    print("中文影视剧英文名查找工具")
    print("=" * 60)
    print()
    
    # 获取输入
    names = []
    
    # 方式1: 命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--file' or sys.argv[1] == '-f':
            # 从文件读取
            if len(sys.argv) > 2:
                filepath = sys.argv[2]
                names = load_names_from_file(filepath)
                print(f"从文件加载了 {len(names)} 个名称: {filepath}")
            else:
                print("错误: 请指定文件路径")
                print("用法: python find_english_names.py --file 文件名.txt")
                return
        else:
            # 直接输入名称
            names = sys.argv[1:]
            print(f"输入了 {len(names)} 个名称")
    else:
        # 交互式输入
        print("请输入要查找的中文影视剧名称（每行一个，输入空行结束）:")
        print("提示: 也可以使用 --file 参数从文件批量导入")
        print()
        while True:
            name = input("> ").strip()
            if not name:
                break
            names.append(name)
    
    if not names:
        print("\n错误: 没有输入任何名称")
        print("\n使用方法:")
        print("  1. 交互式输入: python find_english_names.py")
        print("  2. 命令行输入: python find_english_names.py 剧名1 剧名2 ...")
        print("  3. 文件批量导入: python find_english_names.py --file 文件名.txt")
        return
    
    print(f"\n开始搜索 {len(names)} 个影视剧的英文名称...")
    print("=" * 60)
    
    all_results = []
    
    for i, name in enumerate(names, 1):
        print(f"\n[{i}/{len(names)}] 处理: {name}")
        result = search_all_sources(name)
        all_results.append(result)
        
        # 显示结果摘要
        found = []
        if result['tmdb']:
            found.append(f"TMDB: {result['tmdb'].get('title', 'N/A')}")
        if result['douban']:
            found.append(f"豆瓣: {result['douban'].get('title', 'N/A')}")
        
        if found:
            print(f"  ✓ 找到: {' | '.join(found)}")
        else:
            print(f"  ✗ 未找到结果")
        
        # 每10个休息一下
        if i % 10 == 0 and i < len(names):
            print(f"\n已处理 {i} 个，休息3秒...")
            time.sleep(3)
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f'english_names_{timestamp}.csv'
    json_file = f'english_names_{timestamp}.json'
    
    readme_file = save_results_to_csv(all_results, csv_file)
    save_results_to_json(all_results, json_file)
    
    # 统计
    found_tmdb = sum(1 for r in all_results if r['tmdb'])
    found_douban = sum(1 for r in all_results if r['douban'])
    found_any = sum(1 for r in all_results if r['tmdb'] or r['douban'])
    
    print("\n" + "=" * 60)
    print("搜索完成！")
    print("=" * 60)
    print(f"总计: {len(names)} 个")
    print(f"找到结果: {found_any} 个 ({found_any/len(names)*100:.1f}%)")
    print(f"  - TMDB: {found_tmdb} 个")
    print(f"  - 豆瓣: {found_douban} 个")
    print(f"\n结果已保存:")
    print(f"  - CSV文件: {csv_file}")
    print(f"  - JSON文件: {json_file}")
    print(f"  - 格式说明: {readme_file}")
    print("=" * 60)
    print("\n📋 CSV文件已优化！")
    print("- 支持自动换行和最优列宽")
    print("- 查看格式说明文件了解Excel使用技巧")
    print("- 在Excel中打开后建议启用'自动换行'功能")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

