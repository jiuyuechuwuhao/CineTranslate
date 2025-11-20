#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能影视名称提取器
支持多种复杂格式的影视剧名称自动识别
"""

import re
from typing import List, Dict, Tuple
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MovieNameExtractor:
    """智能影视名称提取器"""
    
    def __init__(self):
        # 定义各种正则表达式模式
        self.patterns = {
            # 年份 + 《名称》格式
            'year_with_title': re.compile(r'(\d{4})\s*[年]?\s*[《]([^》]+)[》]', re.UNICODE),
            
            # 纯《名称》格式
            'title_only': re.compile(r'[《]([^》]+)[》]', re.UNICODE),
            
            # 英文引号格式
            'english_quotes': re.compile(r'["]([^"]+)["]', re.UNICODE),
            
            # 中文引号格式
            'chinese_quotes': re.compile(r'["]([^"]+)["]', re.UNICODE),
            
            # 方括号格式
            'square_brackets': re.compile(r'[\[]([^\]]+)[\]]', re.UNICODE),
            
            # 可能的影视名称（基于常见关键词）
            'potential_title': re.compile(r'(?:电视剧|电影|影片|剧名|作品)\s*[：:]?\s*([^，。！？；\n]+)', re.UNICODE),
        }
        
        # 常见影视相关关键词，用于排除非影视内容
        self.movie_keywords = {
            '电视剧', '电影', '影片', '剧名', '作品', '主演', '导演', 
            '上映', '播出', '集数', '季', '部', '版', '重制', '续集',
            '预告', '海报', '票房', '评分', '影评', '剧评'
        }
        
        # 常见演员姓名，用于过滤（基于中国常见演员）
        self.actor_names = {
            # 肖战相关
            '肖战', '王一博', '杨紫', '李现', '赵丽颖', '杨幂', '迪丽热巴',
            '鹿晗', '吴亦凡', '黄子韬', '杨洋', '李易峰', '井柏然', '付辛博',
            '唐嫣', '刘亦菲', '刘诗诗', '佟丽娅', '古力娜扎', '郑爽', '周冬雨',
            '马思纯', '倪妮', 'Angelababy', '范冰冰', '李冰冰', '周迅', '赵薇',
            '章子怡', '巩俐', '徐静蕾', '张静初', '高圆圆', '贾静雯', '林心如',
            '范冰冰', '姚晨', '海清', '马伊琍', '袁泉', '秦海璐', '刘涛', '蒋欣',
            '王子文', '杨紫', '乔欣', '关晓彤', '欧阳娜娜', '宋祖儿', '林允',
            '张婧仪', '周奇', '成毅', '白鹿', '曾舜晞', '邓为', '向涵之',
            '卢昱晓', '王星越', '肖战', '张婧仪', '周奇', '成毅', '古力娜扎',
            '卢昱晓', '王星越', '白鹿', '曾舜晞', '邓为', '向涵之'
        }
        
        # 常见无效词组模式
        self.invalid_patterns = [
            r'由\w+、?\w*主演',  # 由某某主演
            r'\w+、?\w*主演的',   # 某某主演的
            r'\w+、?\w*主演',     # 某某主演
            r'导演[:：]\w+',      # 导演：某某
            r'主演[:：]\w+',      # 主演：某某
            r'\d+年\d+月\d+日',   # 日期
            r'\d+月\d+日',       # 月日
            r'\d+年\d+月',       # 年月
            r'\d+月\d+日',       # 月日
        ]
        
        # 常见分隔符
        self.separators = [',', '，', ';', '；', '|', '/', '、', '\n', ' ']
    
    def extract_from_year_title_format(self, text: str) -> List[Dict[str, any]]:
        """提取年份+《名称》格式"""
        results = []
        matches = self.patterns['year_with_title'].findall(text)
        
        for year, title in matches:
            title = title.strip()
            if self._is_valid_movie_title(title):
                results.append({
                    'title': title,
                    'year': year,
                    'format': 'year_with_title',
                    'confidence': 0.95,
                    'original_text': f"{year}年《{title}》"
                })
                logger.info(f"提取到年份+标题格式: {year}年《{title}》")
        
        return results
    
    def extract_from_title_only_format(self, text: str) -> List[Dict[str, any]]:
        """提取纯《名称》格式"""
        results = []
        matches = self.patterns['title_only'].findall(text)
        
        for title in matches:
            title = title.strip()
            if self._is_valid_movie_title(title):
                # 检查是否已经被年份+标题格式提取过
                if not self._is_already_extracted(results, title):
                    confidence = self._calculate_title_confidence(title, text)
                    results.append({
                        'title': title,
                        'year': None,
                        'format': 'title_only',
                        'confidence': confidence,
                        'original_text': f"《{title}》"
                    })
                    logger.info(f"提取到纯标题格式: 《{title}》")
        
        return results
    
    def extract_from_quotes_format(self, text: str) -> List[Dict[str, any]]:
        """提取引号格式"""
        results = []
        
        # 英文引号
        matches = self.patterns['english_quotes'].findall(text)
        for title in matches:
            title = title.strip()
            if self._is_valid_movie_title(title) and len(title) > 2:
                confidence = self._calculate_title_confidence(title, text)
                results.append({
                    'title': title,
                    'year': None,
                    'format': 'english_quotes',
                    'confidence': confidence * 0.8,  # 引号格式置信度稍低
                    'original_text': f'"{title}"'
                })
        
        # 中文引号
        matches = self.patterns['chinese_quotes'].findall(text)
        for title in matches:
            title = title.strip()
            if self._is_valid_movie_title(title) and len(title) > 2:
                confidence = self._calculate_title_confidence(title, text)
                results.append({
                    'title': title,
                    'year': None,
                    'format': 'chinese_quotes',
                    'confidence': confidence * 0.8,
                    'original_text': f'"{title}"'
                })
        
        return results
    
    def extract_from_square_brackets(self, text: str) -> List[Dict[str, any]]:
        """提取方括号格式"""
        results = []
        matches = self.patterns['square_brackets'].findall(text)
        
        for title in matches:
            title = title.strip()
            if self._is_valid_movie_title(title) and len(title) > 2:
                confidence = self._calculate_title_confidence(title, text)
                results.append({
                    'title': title,
                    'year': None,
                    'format': 'square_brackets',
                    'confidence': confidence * 0.7,  # 方括号格式置信度更低
                    'original_text': f'[{title}]'
                })
        
        return results
    
    def extract_from_separated_text(self, text: str) -> List[Dict[str, any]]:
        """从分隔文本中提取可能的影视名称（简化版，专注书名号）"""
        results = []
        
        # 如果文本中包含书名号，直接返回空列表，让书名号专用方法处理
        if '《' in text and '》' in text:
            return results
        
        # 只有当没有书名号时才进行分隔符提取
        # 使用多种分隔符分割文本
        for separator in self.separators:
            if separator in text:
                parts = text.split(separator)
                for part in parts:
                    part = part.strip()
                    # 跳过空内容
                    if not part:
                        continue
                    
                    # 预检查：快速排除明显无效的内容
                    if self._is_quick_invalid(part):
                        continue
                    
                    # 排除包含书名号等特殊字符的部分
                    if any(char in part for char in ['《', '》', '"', '"', '[', ']']):
                        continue
                    
                    # 清理结尾的标点符号
                    part = re.sub(r'[，。！？；：:,;|/、]+$', '', part).strip()
                    
                    # 最终长度检查
                    if len(part) < 2 or len(part) > 25:
                        continue
                    
                    if self._is_potential_movie_title(part):
                        confidence = self._calculate_title_confidence(part, text)
                        if confidence > 0.4:  # 提高最低置信度阈值
                            results.append({
                                'title': part,
                                'year': None,
                                'format': 'separated_text',
                                'confidence': confidence,
                                'original_text': part
                            })
        
        return results
    
    def _is_quick_invalid(self, text: str) -> bool:
        """快速预检查，排除明显无效的内容"""
        # 过短或过长
        if len(text) < 2 or len(text) > 30:
            return True
        
        # 纯数字
        if text.isdigit():
            return True
        
        # 包含明显的人名指示词或结构
        person_indicators = ['主演的', '主演', '导演', '饰演', '扮演', '出演', '参演']
        for indicator in person_indicators:
            if indicator in text:
                return True
        
        # 检查是否以"由"开头且后面跟着人名（如"由邓为"）
        if text.startswith('由') and len(text) <= 5:
            return True
            
        # 检查是否包含顿号分隔的人名结构
        if '、' in text and any(actor in text for actor in ['主演', '导演', '饰演']):
            return True
        
        # 匹配演员姓名
        if text in self.actor_names:
            return True
        
        # 包含无效模式
        for pattern in self.invalid_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def extract_all(self, text: str) -> List[Dict[str, any]]:
        """提取所有可能的影视名称"""
        if not text or not text.strip():
            return []
        
        all_results = []
        
        # 1. 优先提取年份+《名称》格式（最高优先级）
        year_title_results = self.extract_from_year_title_format(text)
        all_results.extend(year_title_results)
        
        # 2. 提取纯《名称》格式
        title_only_results = self.extract_from_title_only_format(text)
        all_results.extend(title_only_results)
        
        # 3. 提取引号格式
        quotes_results = self.extract_from_quotes_format(text)
        all_results.extend(quotes_results)
        
        # 4. 提取方括号格式
        bracket_results = self.extract_from_square_brackets(text)
        all_results.extend(bracket_results)
        
        # 5. 从分隔文本中提取（最低优先级）
        separated_results = self.extract_from_separated_text(text)
        all_results.extend(separated_results)
        
        # 去重和排序
        unique_results = self._remove_duplicates(all_results)
        sorted_results = sorted(unique_results, key=lambda x: x['confidence'], reverse=True)
        
        logger.info(f"总共提取到 {len(sorted_results)} 个影视名称")
        return sorted_results
    
    def _is_valid_movie_title(self, title: str) -> bool:
        """判断是否为有效的影视名称"""
        if not title or len(title) < 2 or len(title) > 50:
            return False
        
        # 排除纯数字
        if title.isdigit():
            return False
        
        # 排除演员姓名
        if title in self.actor_names:
            logger.info(f"排除演员姓名: {title}")
            return False
        
        # 排除明显的非影视内容
        invalid_keywords = {
            '第', '章', '节', '页', '段', '列', '个', '条', '款',
            '说明', '注意', '提示', '警告', '错误', '失败', '成功',
            '主演', '导演', '演员', '配角', '角色', '人物', '主角'
        }
        
        for keyword in invalid_keywords:
            if keyword in title and len(title) < 8:  # 放宽长度限制，但严格过滤
                return False
        
        # 检查是否匹配无效模式
        for pattern in self.invalid_patterns:
            if re.search(pattern, title):
                logger.info(f"排除匹配无效模式: {title}")
                return False
        
        return True
    
    def _is_potential_movie_title(self, text: str) -> bool:
        """判断是否为潜在的影视名称"""
        if not self._is_valid_movie_title(text):
            return False
        
        # 检查是否包含影视相关关键词
        for keyword in self.movie_keywords:
            if keyword in text:
                return True
        
        # 检查是否看起来像中文影视名称
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        if chinese_chars >= 2:
            return True
        
        # 检查是否看起来像英文影视名称
        if text.istitle() and len(text.split()) <= 5:
            return True
        
        return False
    
    def _calculate_title_confidence(self, title: str, original_text: str) -> float:
        """计算标题的置信度"""
        confidence = 0.5  # 基础置信度
        
        # 长度因素
        title_length = len(title)
        if 3 <= title_length <= 20:
            confidence += 0.2
        elif title_length > 20:
            confidence -= 0.1
        
        # 中文影视名称特征
        chinese_chars = sum(1 for char in title if '\u4e00' <= char <= '\u9fff')
        if chinese_chars >= 2:
            confidence += 0.3
        
        # 包含影视关键词
        for keyword in self.movie_keywords:
            if keyword in original_text:
                confidence += 0.2
                break
        
        # 上下文环境
        context_keywords = ['2025', '2024', '2023', '2022', '2021', '2020']
        for keyword in context_keywords:
            if keyword in original_text:
                confidence += 0.1
                break
        
        return min(confidence, 1.0)  # 置信度不超过1.0
    
    def _is_already_extracted(self, existing_results: List[Dict], title: str) -> bool:
        """检查是否已经被提取过"""
        for result in existing_results:
            if result['title'] == title:
                return True
        return False
    
    def _remove_duplicates(self, results: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """去除重复结果"""
        seen = set()
        unique_results = []
        
        for result in results:
            title = result['title']
            if title not in seen:
                seen.add(title)
                unique_results.append(result)
            else:
                # 如果重复，保留置信度更高的
                existing = next(r for r in unique_results if r['title'] == title)
                if result['confidence'] > existing['confidence']:
                    unique_results.remove(existing)
                    unique_results.append(result)
        
        return unique_results
    
    def extract_titles_only(self, text: str) -> List[str]:
        """只提取标题名称（简化接口）"""
        results = self.extract_all(text)
        return [result['title'] for result in results]

# 测试函数
def test_extractor():
    """测试提取器"""
    extractor = MovieNameExtractor()
    
    # 测试用例
    test_cases = [
        "2025 年《驻站》《真心英雄》《北上》",
        "《蛮好的人生》《生万物》《庆余年》第二季",
        "最近在看\"流浪地球\"和\"三体\"，都挺不错的",
        "推荐几部好剧：庆余年, 琅琊榜, 知否知否",
        "2024年热门电视剧《繁花》《大江大河》《山海情》",
        "电影[肖申克的救赎]和[阿甘正传]都是经典"
    ]
    
    for test_case in test_cases:
        print(f"\n测试文本: {test_case}")
        results = extractor.extract_all(test_case)
        for result in results:
            print(f"  提取到: {result['title']} (置信度: {result['confidence']:.2f}, 格式: {result['format']})")

if __name__ == "__main__":
    test_extractor()