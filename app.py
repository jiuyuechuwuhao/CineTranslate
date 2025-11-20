#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影视剧英文名查找工具 - Web UI版本
基于Flask的现代Web界面
"""

from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import os
import sys
import json
import csv
from datetime import datetime
from io import StringIO, BytesIO
import tempfile
import threading
import time

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from find_english_names import search_all_sources, format_text_for_excel
from movie_name_extractor import MovieNameExtractor

app = Flask(__name__)
app.secret_key = 'movie-finder-secret-key-2024'

# 全局变量存储搜索结果
search_results = []
current_session = {}

# 初始化智能提取器
movie_extractor = MovieNameExtractor()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """搜索影视剧英文名"""
    global search_results, current_session
    
    data = request.get_json()
    movie_names = data.get('movies', [])
    
    if not movie_names:
        return jsonify({'error': '请输入至少一个影视剧名称'})
    
    # 清理输入数据
    movie_names = [name.strip() for name in movie_names if name.strip()]
    
    if not movie_names:
        return jsonify({'error': '请输入有效的影视剧名称'})
    
    results = []
    total = len(movie_names)
    
    for i, name in enumerate(movie_names, 1):
        try:
            result = search_all_sources(name)
            results.append(result)
            
            # 每10个休息一下，避免过于频繁的请求
            if i % 10 == 0 and i < total:
                time.sleep(3)
            else:
                time.sleep(1.5)  # 正常的请求间隔
                
        except Exception as e:
            # 如果某个搜索失败，记录错误但继续处理其他的
            results.append({
                'chinese_name': name,
                'tmdb': None,
                'douban': None,
                'error': str(e)
            })
    
    search_results = results
    current_session = {
        'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
        'total': total,
        'found_tmdb': sum(1 for r in results if r.get('tmdb')),
        'found_douban': sum(1 for r in results if r.get('douban')),
        'found_any': sum(1 for r in results if r.get('tmdb') or r.get('douban'))
    }
    
    return jsonify({
        'success': True,
        'results': results,
        'statistics': current_session
    })

@app.route('/export/csv')
def export_csv():
    """导出CSV文件"""
    global search_results, current_session
    
    if not search_results:
        flash('请先进行搜索再导出结果', 'warning')
        return redirect(url_for('index'))
    
    # 创建CSV内容
    output = StringIO()
    writer = csv.writer(output)
    
    # 写入标题行（更新版，统一显示格式）
    headers = ['中文名称', 'TMDB英文名称', 'TMDB链接', '豆瓣英文名称', '豆瓣链接', '最佳匹配（推荐）', '备注']
    writer.writerow(headers)
    
    # 分析数据以确定最佳列宽（更新版，包含备注列）
    max_lengths = {
        'chinese_name': 10,
        'tmdb_title': 15,
        'tmdb_link': 30,
        'douban_title': 15,
        'douban_link': 30,
        'best_match': 15,
        'notes': 20
    }
    
    # 分析所有数据以确定最大长度（更新版，包含备注）
    for result in search_results:
        # 中文名称长度
        max_lengths['chinese_name'] = max(max_lengths['chinese_name'], len(result['chinese_name']))
        
        # TMDB数据长度
        if result.get('tmdb'):
            max_lengths['tmdb_title'] = max(max_lengths['tmdb_title'], len(result['tmdb'].get('title', '')))
            max_lengths['tmdb_link'] = max(max_lengths['tmdb_link'], len(result['tmdb'].get('link', '')))
        
        # 豆瓣数据长度
        if result.get('douban'):
            douban_title = result['douban'].get('title', '')
            max_lengths['douban_title'] = max(max_lengths['douban_title'], len(douban_title))
            max_lengths['douban_link'] = max(max_lengths['douban_link'], len(result['douban'].get('link', '')))
            
            # 检查是否有备注信息
            if result['douban'].get('note'):
                max_lengths['notes'] = max(max_lengths['notes'], len(result['douban'].get('note', '')))
        
        # 最佳匹配长度
        best_match = ''
        if result.get('tmdb'):
            best_match = result['tmdb'].get('title', '')
        elif result.get('douban'):
            best_match = result['douban'].get('title', '')
        max_lengths['best_match'] = max(max_lengths['best_match'], len(best_match))
    
    # 设置最大列宽限制，避免过宽
    for key in max_lengths:
        max_lengths[key] = min(max_lengths[key], 80)  # 最大80字符
    
    # 写入数据行
    for result in search_results:
        row = []
        
        # 中文名称 - 格式化
        chinese_name = format_text_for_excel(result['chinese_name'], max_lengths['chinese_name'])
        row.append(chinese_name)
        
        # TMDB - 格式化标题和链接
        if result.get('tmdb'):
            tmdb_title = format_text_for_excel(result['tmdb'].get('title', ''), max_lengths['tmdb_title'])
            tmdb_link = format_text_for_excel(result['tmdb'].get('link', ''), max_lengths['tmdb_link'])
            row.extend([tmdb_title, tmdb_link])
        else:
            row.extend(['无', '无'])
        
        # 豆瓣 - 格式化标题和链接
        if result.get('douban'):
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
        if result.get('tmdb'):
            best_match = result['tmdb'].get('title', '')
        elif result.get('douban'):
            has_english = result['douban'].get('has_english', True)
            if has_english:
                best_match = result['douban'].get('title', '')
            else:
                best_match = '无'  # 只有中文名时显示"无"
        best_match_formatted = format_text_for_excel(best_match, max_lengths['best_match'])
        row.append(best_match_formatted)
        
        # 备注信息（标注数据来源平台和具体情况）
        notes = ''
        has_tmdb = bool(result.get('tmdb'))
        has_douban = bool(result.get('douban'))
        
        # 确定数据来源平台
        if has_tmdb and has_douban:
            platform_note = '双平台'
        elif has_tmdb:
            platform_note = 'TMDB平台'
        elif has_douban:
            platform_note = '豆瓣平台'
        else:
            platform_note = '未找到'
        
        # 获取具体的备注信息
        detail_notes = []
        if has_douban and result['douban'].get('note'):
            detail_notes.append(result['douban']['note'])
        elif has_tmdb and result['tmdb'].get('note'):
            detail_notes.append(result['tmdb']['note'])
        
        # 组合平台和详细信息
        if detail_notes:
            notes = f"{platform_note} | {' | '.join(detail_notes)}"
        else:
            notes = platform_note
            
        notes_formatted = format_text_for_excel(notes, max_lengths['notes'])
        row.append(notes_formatted)
        
        writer.writerow(row)
    
    # 准备文件下载
    output.seek(0)
    filename = f"movie_english_names_{current_session.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))}.csv"
    
    return send_file(
        BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/export/json')
def export_json():
    """导出JSON文件"""
    global search_results, current_session
    
    if not search_results:
        flash('请先进行搜索再导出结果', 'warning')
        return redirect(url_for('index'))
    
    # 创建JSON内容
    json_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_movies': current_session.get('total', 0),
            'found_tmdb': current_session.get('found_tmdb', 0),
            'found_douban': current_session.get('found_douban', 0),
            'found_any': current_session.get('found_any', 0)
        },
        'results': search_results
    }
    
    json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
    
    filename = f"movie_english_names_{current_session.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))}.json"
    
    return send_file(
        BytesIO(json_str.encode('utf-8')),
        mimetype='application/json',
        as_attachment=True,
        download_name=filename
    )

@app.route('/export/txt')
def export_txt():
    """导出TXT简洁版文件 - 只包含中文名+最佳英文名"""
    global search_results, current_session
    
    if not search_results:
        flash('请先进行搜索再导出结果', 'warning')
        return redirect(url_for('index'))
    
    # 创建简洁的TXT内容
    lines = []
    for result in search_results:
        chinese_name = result['chinese_name']
        
        # 获取最佳匹配的英文名（TMDB始终优先，只有TMDB没有结果时才使用豆瓣）
        best_english = ''
        if result.get('tmdb') and result['tmdb'].get('title'):
            best_english = result['tmdb']['title']
        elif result.get('douban') and result['douban'].get('title'):
            # 检查豆瓣是否有英文名
            has_english = result['douban'].get('has_english', True)
            if has_english:
                best_english = result['douban']['title']
            else:
                best_english = '无'  # 只有中文名时显示"无"
        
        # 如果有英文名，格式为：中文名 + 英文名
        # 如果没有英文名，只显示中文名
        if best_english:
            lines.append(f"{chinese_name} {best_english}")
        else:
            lines.append(chinese_name)
    
    txt_content = '\n'.join(lines)
    
    filename = f"movie_names_simple_{current_session.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))}.txt"
    
    return send_file(
        BytesIO(txt_content.encode('utf-8-sig')),
        mimetype='text/plain',
        as_attachment=True,
        download_name=filename
    )

@app.route('/extract_names', methods=['POST'])
def extract_names():
    """智能提取影视名称"""
    try:
        data = request.get_json()
        raw_text = data.get('text', '')
        
        if not raw_text or not raw_text.strip():
            return jsonify({'error': '请输入文本内容'})
        
        # 使用智能提取器提取影视名称
        extracted_results = movie_extractor.extract_all(raw_text)
        
        # 获取仅标题列表（去重并按置信度排序）
        titles = [result['title'] for result in extracted_results]
        
        # 返回详细信息
        return jsonify({
            'success': True,
            'extracted_count': len(titles),
            'titles': titles,
            'details': extracted_results
        })
        
    except Exception as e:
        return jsonify({'error': f'提取失败: {str(e)}'})

@app.route('/about')
def about():
    """关于页面"""
    return render_template('about.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, error_message='页面未找到'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, error_message='服务器内部错误'), 500

if __name__ == '__main__':
    # 检查必要的依赖
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as e:
        print(f"缺少必要的依赖包: {e}")
        print("请运行: pip install requests beautifulsoup4 flask")
        sys.exit(1)
    
# Vercel serverless适配
if __name__ == '__main__':
    # 本地运行时使用的配置
    print("🎬 启动影视剧英文名查找工具 Web UI...")
    print("📱 请打开浏览器访问: http://localhost:8084")
    app.run(debug=True, host='0.0.0.0', port=8084)
