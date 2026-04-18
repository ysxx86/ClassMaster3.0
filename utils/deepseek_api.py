# -*- coding: utf-8 -*-
import os
import json
import requests
import logging
import time
import random
from typing import Dict, Any, Optional
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekAPI:
    """DeepSeek API封装类，用于调用DeepSeek AI大模型生成学生评语"""

    # API端点
    API_URL = "https://api.deepseek.com/chat/completions"
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化DeepSeek API客户端

        Args:
            api_key: DeepSeek API密钥，如果不提供则从环境变量获取
        """
        # 检查传入的API密钥是否有效
        if api_key and api_key.strip():
            self.api_key = api_key.strip()
            logger.info("使用自定义DeepSeek API密钥")
        elif os.environ.get("DEEPSEEK_API_KEY", "").strip():
            self.api_key = os.environ.get("DEEPSEEK_API_KEY").strip()
            logger.info("使用环境变量中的DeepSeek API密钥")
        else:
            raise ValueError("DeepSeek API密钥未设置。请在 .env 文件或环境变量中设置 DEEPSEEK_API_KEY")

        if not self.api_key.startswith("sk-"):
            logger.warning(f"DeepSeek API密钥格式可能不正确: {self.api_key[:5]}...")
    
    def update_api_key(self, api_key: str) -> None:
        """更新API密钥
        
        Args:
            api_key: 新的API密钥
        """
        if api_key and api_key.strip():
            self.api_key = api_key.strip()
            logger.info("DeepSeek API密钥已更新")
            return True
        return False
    
    def test_connection(self) -> Dict[str, Any]:
        """测试API连接是否正常
        
        Returns:
            包含测试结果的字典，格式为 {"status": "success|error", "message": "..."}
        """
        if not self.api_key:
            return {
                "status": "error",
                "message": "未设置API密钥，无法测试连接"
            }
            
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 构建一个简单的请求体
        payload = {
            "model": "deepseek-reasoner",
            "messages": [
                {"role": "system", "content": "你是一个简单的API测试助手。"},
                {"role": "user", "content": "返回'连接测试成功'这几个字，不要返回其他内容。"}
            ],
            "max_tokens": 10
        }
        
        try:
            # 发送请求
            logger.info("正在测试DeepSeek API连接...")
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=15)
            response.raise_for_status()  # 检查HTTP错误
            
            # 解析响应
            result = response.json()
            
            # 检查响应是否包含预期字段
            if "choices" in result and len(result["choices"]) > 0:
                # 获取消息内容
                message = result["choices"][0]["message"]
                
                # 检查是否存在content或reasoning_content任一字段
                if "content" in message or "reasoning_content" in message:
                    logger.info("DeepSeek API连接测试成功")
                    return {
                        "status": "success",
                        "message": "API连接正常"
                    }
                else:
                    logger.warning(f"API响应格式异常: {result}")
                    return {
                        "status": "error",
                        "message": "API响应格式异常，但连接成功"
                    }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API连接测试失败: {str(e)}")
            return {
                "status": "error",
                "message": f"API连接失败: {str(e)}"
            }
        except json.JSONDecodeError:
            logger.error("API返回的不是有效的JSON格式")
            return {
                "status": "error",
                "message": "API返回格式错误"
            }
        except Exception as e:
            logger.error(f"API连接测试时发生未知错误: {str(e)}")
            return {
                "status": "error",
                "message": f"API连接测试失败: {str(e)}"
            }
    
    def generate_comment(self, 
                        student_info: Dict[str, Any], 
                        style: str = "鼓励性的", 
                        tone: str = "正式的", 
                        max_length: int = 50000,
                        min_length: int = 200) -> Dict[str, Any]:
        """生成学生评语
        
        Args:
            student_info: 学生信息，包含姓名、性别、特点、爱好等
            style: 评语风格，如"鼓励性的"、"严肃的"、"中肯的"等
            tone: 评语语气，如"正式的"、"亲切的"、"严厉的"等
            max_length: 思考过程(reasoning_content)最大字数，默认50000字
            min_length: 评语最小字数，默认200字
            
        Returns:
            包含生成评语的字典，格式为 {"status": "ok|error", "comment": "...", "message": "..."}
        """
        logger.info(f"开始为学生 {student_info.get('name')} 生成评语")
        logger.info(f"学生特征信息: 个性特点={student_info.get('personality', '未提供')}, 学习表现={student_info.get('study_performance', '未提供')}, 爱好={student_info.get('hobbies', '未提供')}, 待改进={student_info.get('improvement', '未提供')}")
        
        # 设置最终评语(content字段)的长度限制
        content_max_length = 260
        content_min_length = 200
        
        # 保留传入的max_length参数，用于控制思考过程(reasoning_content)的长度
        reasoning_max_length = max_length
        
        if not self.api_key:
            logger.error("API密钥未设置，无法调用API")
            return {
                "status": "error", 
                "message": "未设置DeepSeek API密钥，无法调用API",
                "comment": ""
            }

        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 构建提示语
        gender = "他" if student_info.get("gender") == "男" else "她"
        
        # 获取额外指令
        additional_instructions = student_info.get('additional_instructions', '')
        
        # 检查是否有提供学生特征信息
        has_personality = student_info.get('personality', '').strip() != ''
        has_study_info = student_info.get('study_performance', '').strip() != ''
        has_hobbies = student_info.get('hobbies', '').strip() != ''
        has_improvement = student_info.get('improvement', '').strip() != ''
        
        prompt = f"""
你是一名经验丰富的班主任，请为以下学生生成一段评语。

【核心指令】
- 直接生成评语，不在评语正文里显示统计的字数。
- 评语必须是{style}和{tone}的

学生信息:
- 姓名: {student_info.get('name', '学生')}
- 性别: {student_info.get('gender', '未知')}
- 个性特点: {student_info.get('personality', '未提供')}
- 学习表现: {student_info.get('study_performance', '未提供')}
- 课外活动/爱好: {student_info.get('hobbies', '未提供')}
- 需要改进的方面: {student_info.get('improvement', '未提供')}

仅输出评语，不要任何其他内容。
"""

        # 根据是否提供了特征信息添加额外指导
        if has_personality or has_study_info or has_hobbies or has_improvement:
            prompt += "\n要点：\n"
            
            if has_personality:
                prompt += f"- 突出个性特点：{student_info.get('personality')}\n"
            
            if has_study_info:
                prompt += f"- 反映学习表现：{student_info.get('study_performance')}\n"
            
            if has_hobbies:
                prompt += f"- 肯定爱好特长：{student_info.get('hobbies')}\n"
            
            if has_improvement:
                prompt += f"- 改进建议：针对\"{student_info.get('improvement')}\"\n"
        else:
            # 如果没有提供特征信息，强调多样性和随机性
            prompt += """
特点：
- 随机创造性地生成评语
- 避免模板化表达
- 避免开头都是春日、春风等固定式开头。
"""

        # 特别强调诗意风格的要求
        if style == "诗意的":
            prompt += """
【诗意风格】
- 在评语中引用一句与学生特点相关的古诗词名句，带引号和出处
- 整体评语保持文学性，与诗词风格一致
"""

        # 添加额外指令和结束提示
        prompt += f"""
{additional_instructions}
不要在回复中写除了评语之外的任何内容。
"""

        # 构建请求体
        payload = {
            "model": "deepseek-reasoner",
            "messages": [
                {"role": "system", "content": "直接生成235字左右学生评语。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 5000,
            "temperature": 0.9,
            "top_p": 0.95,
            "frequency_penalty": 0.3,
            "presence_penalty": 0.3
        }
        
        # 初始化重试计数
        attempts = 0
        max_attempts = 3
        base_timeout = 180  # 基础超时时间，单位为秒
        
        while attempts < max_attempts:
            try:
                attempts += 1
                current_timeout = base_timeout * (1 + attempts * 0.5)  # 逐渐增加超时时间
                
                logger.info(f"正在调用DeepSeek API生成评语（尝试 {attempts}/{max_attempts}，超时设置: {current_timeout}秒）...")
                
                # 发送请求
                response = requests.post(
                    self.API_URL, 
                    headers=headers, 
                    json=payload, 
                    timeout=current_timeout  # 设置更长的超时时间，避免超时问题
                )
                
                # 检查HTTP错误
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                
                # 检查是否有有效内容
                if "choices" in result and len(result["choices"]) > 0:
                    # 获取消息内容
                    message = result["choices"][0]["message"]
                    
                    # 处理DeepSeek-Reasoner模型返回的reasoning_content字段
                    reasoning_content = message.get("reasoning_content", "")
                    content = message.get("content", "")
                    original_content = content  # 保存原始content字段
                    
                    # 只有当content为空且reasoning_content不为空时，才使用reasoning_content作为评语内容
                    if not content.strip() and reasoning_content:
                        logger.info(f"content为空，使用reasoning_content作为评语内容，长度：{len(reasoning_content)}字符")
                        content = reasoning_content
                    
                    # 清理内容，去除多余的引号和空格
                    content = content.strip()
                    
                    logger.info(f"成功获取评语，评语长度: {len(content)}字")
                    
                    # 检查评语长度，严格限制不超过content_max_length
                    if len(content) > content_max_length:
                        logger.warning(f"评语超出最大长度限制，当前长度: {len(content)}，最大允许: {content_max_length}")
                        content = self._truncate_to_complete_sentence(content, content_max_length)
                        logger.info(f"截断后评语长度: {len(content)}字")
                    
                    # 返回结果
                    return {
                        "status": "ok",
                        "comment": content,
                        "message": "评语生成成功",
                        "reasoning_content": reasoning_content,
                        "content_field": original_content
                    }
                else:
                    logger.warning(f"API响应缺少有效内容: {result}")
                    
                    # 最后一次尝试失败时返回错误
                    if attempts >= max_attempts:
                        return {
                            "status": "error",
                            "comment": "",
                            "message": "API返回内容无效"
                        }
                    
                    # 否则准备重试
                    logger.info(f"准备进行第 {attempts+1}/{max_attempts} 次尝试...")
                    time.sleep(min(2 * attempts, 5))  # 重试前等待，时间随尝试次数增加
                    
            except requests.exceptions.Timeout as e:
                logger.warning(f"API请求超时 (尝试 {attempts}/{max_attempts}): {str(e)}")
                
                # 最后一次尝试失败时返回错误
                if attempts >= max_attempts:
                    return {
                        "status": "error",
                        "comment": "",
                        "message": f"API请求失败: {str(e)}"
                    }
                
                # 否则准备重试
                retry_wait = min(5 * attempts + random.uniform(0.5, 2.0), 15)  # 增加随机性避免同时重试
                logger.info(f"等待 {retry_wait:.1f} 秒后进行第 {attempts+1}/{max_attempts} 次尝试...")
                time.sleep(retry_wait)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"API请求错误 (尝试 {attempts}/{max_attempts}): {str(e)}")
                
                # 最后一次尝试失败时返回错误
                if attempts >= max_attempts:
                    return {
                        "status": "error",
                        "comment": "",
                        "message": f"API请求失败: {str(e)}"
                    }
                
                # 否则准备重试
                retry_wait = min(3 * attempts, 10)
                logger.info(f"等待 {retry_wait} 秒后进行第 {attempts+1}/{max_attempts} 次尝试...")
                time.sleep(retry_wait)
                
            except json.JSONDecodeError as e:
                logger.error(f"API返回的不是有效的JSON格式 (尝试 {attempts}/{max_attempts}): {str(e)}")
                
                # 这种错误可能是服务器问题，尝试重试
                if attempts >= max_attempts:
                    return {
                        "status": "error",
                        "comment": "",
                        "message": "API返回格式错误"
                    }
                
                time.sleep(min(2 * attempts, 8))
                
            except Exception as e:
                logger.error(f"评语生成时发生未知错误 (尝试 {attempts}/{max_attempts}): {str(e)}")
                logger.error(traceback.format_exc())
                
                # 未知错误，返回详细信息
                return {
                    "status": "error",
                    "comment": "",
                    "message": f"生成评语时发生错误: {str(e)}"
                }
        
        # 如果所有尝试都失败，返回错误信息
        return {
            "status": "error",
            "comment": "",
            "message": "多次尝试后仍无法获取评语"
        }
    
    def _truncate_to_complete_sentence(self, text, max_length):
        """将文本截断到指定长度，尽量保持句子完整
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            截断后的文本
        """
        if len(text) <= max_length:
            return text
            
        # 尝试在标点符号处截断
        end_marks = ["。", "！", "？", "：", "；", "……", "，"]
        
        truncated = text[:max_length]
        for mark in end_marks:
            last_mark_pos = truncated.rfind(mark)
            if last_mark_pos > max_length * 0.75:  # 确保截断的文本不会太短
                return text[:last_mark_pos + 1]
        
        # 如果没有找到合适的标点符号，直接截断并确保不超过最大长度
        return truncated
            
    def analyze_exam_paper(self, questions_data, student_scores, subject, exam_name, class_name):
        """分析试卷数据，提供教学建议
        
        Args:
            questions_data: 题目数据，包含每道题的错误率、分值等
            student_scores: 学生成绩数据
            subject: 学科名称
            exam_name: 考试名称
            class_name: 班级名称
            
        Returns:
            包含分析结果的字典，格式为 {"status": "ok|error", "analysis": {...}, "message": "..."}
        """
        logger.info(f"开始分析{subject}试卷: {exam_name}")
        
        if not self.api_key:
            logger.error("API密钥未设置，无法调用API")
            return {
                "status": "error", 
                "message": "未设置DeepSeek API密钥，无法调用API",
                "analysis": {}
            }

        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 分析错误率较高的题目
        high_error_questions = []
        medium_error_questions = []
        for q in questions_data:
            if q['error_rate'] > 0.7:
                high_error_questions.append(q)
            elif q['error_rate'] > 0.4:
                medium_error_questions.append(q)
        
        # 计算全班平均分和分数段分布
        scores = student_scores
        total_students = len(scores)
        if total_students == 0:
            average_score = 0
            pass_rate = 0
            excellent_rate = 0
            score_distribution = {
                "0-59": 0,
                "60-69": 0,
                "70-79": 0,
                "80-89": 0,
                "90-100": 0
            }
        else:
            average_score = sum(scores) / total_students
            pass_count = sum(1 for score in scores if score >= 60)
            excellent_count = sum(1 for score in scores if score >= 90)
            pass_rate = (pass_count / total_students) * 100
            excellent_rate = (excellent_count / total_students) * 100
            
            # 计算分数段分布
            score_distribution = {
                "0-59": sum(1 for score in scores if score < 60),
                "60-69": sum(1 for score in scores if 60 <= score < 70),
                "70-79": sum(1 for score in scores if 70 <= score < 80),
                "80-89": sum(1 for score in scores if 80 <= score < 90),
                "90-100": sum(1 for score in scores if score >= 90)
            }
        
        # 构建提示词
        prompt = f"""
你是一位经验丰富的{subject}教师，请对下面的考试数据进行深入分析，提供详细的教学建议。

考试信息:
- 考试名称: {exam_name}
- 班级: {class_name}
- 学科: {subject}
- 学生人数: {total_students}
- 平均分: {average_score:.2f}
- 及格率: {pass_rate:.2f}%
- 优秀率: {excellent_rate:.2f}%

分数段分布:
- 90-100分: {score_distribution['90-100']}人 ({(score_distribution['90-100']/total_students*100 if total_students > 0 else 0):.2f}%)
- 80-89分: {score_distribution['80-89']}人 ({(score_distribution['80-89']/total_students*100 if total_students > 0 else 0):.2f}%)
- 70-79分: {score_distribution['70-79']}人 ({(score_distribution['70-79']/total_students*100 if total_students > 0 else 0):.2f}%)
- 60-69分: {score_distribution['60-69']}人 ({(score_distribution['60-69']/total_students*100 if total_students > 0 else 0):.2f}%)
- 0-59分: {score_distribution['0-59']}人 ({(score_distribution['0-59']/total_students*100 if total_students > 0 else 0):.2f}%)

高错误率题目 (错误率>70%):
"""

        # 添加高错误率题目信息
        if high_error_questions:
            for q in high_error_questions:
                prompt += f"- 题号{q.get('number', '未知')}, 题型:{q.get('type', '未知')}, 分值:{q.get('score', '未知')}, 错误率:{q.get('error_rate', 0)*100:.2f}%\n"
        else:
            prompt += "- 无高错误率题目\n"
            
        # 添加中等错误率题目信息
        prompt += "\n中等错误率题目 (错误率40%-70%):\n"
        if medium_error_questions:
            for q in medium_error_questions:
                prompt += f"- 题号{q.get('number', '未知')}, 题型:{q.get('type', '未知')}, 分值:{q.get('score', '未知')}, 错误率:{q.get('error_rate', 0)*100:.2f}%\n"
        else:
            prompt += "- 无中等错误率题目\n"
        
        # 完成提示词
        prompt += """
根据以上数据，请提供详细的分析和教学建议，回答需要包含以下几个部分：

1. 总体评价：总结全班考试表现，包括优势和不足
2. 薄弱知识点分析：基于错误率高的题目，分析出学生可能存在的知识漏洞，逐一列出3-5个主要薄弱点
3. 教学建议：针对每个薄弱知识点，提供具体的教学改进方法和课堂活动建议
4. 重难点教学：推荐2-3个针对性的教学方法/活动，帮助学生克服学习困难

请以JSON格式返回分析结果，格式如下：
{
  "overall": "总体评价文本...",
  "weak_points": [
    {
      "title": "薄弱点1标题",
      "description": "薄弱点1详细描述..."
    },
    // 更多薄弱点...
  ],
  "suggestions": [
    {
      "title": "建议1标题",
      "description": "建议1详细描述..."
    },
    // 更多建议...
  ]
}

你的分析必须基于提供的数据，同时结合{subject}学科的特点和教学经验，提供真正有价值的教学指导。
请确保你的JSON格式完全正确，不要包含任何其他文本或说明。
"""

        # 构建请求体
        payload = {
            "model": "deepseek-reasoner",
            "messages": [
                {"role": "system", "content": f"你是一名专业的{subject}教师和教学分析专家，善于分析试卷数据并提供有针对性的教学建议。"},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 2000
        }
        
        try:
            # 发送请求
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()  # 检查HTTP错误
            
            # 解析响应
            result = response.json()
            
            # 检查响应是否包含预期字段
            if "choices" in result and len(result["choices"]) > 0:
                # 获取消息内容
                message = result["choices"][0]["message"]
                
                # 处理DeepSeek-Reasoner模型返回的reasoning_content字段
                reasoning_content = message.get("reasoning_content", "")
                analysis_content = message.get("content", "").strip()
                
                # 如果content为空但reasoning_content不为空，使用reasoning_content
                if not analysis_content and reasoning_content:
                    logger.info(f"content为空，使用reasoning_content，长度：{len(reasoning_content)}字符")
                    analysis_content = reasoning_content.strip()
                
                try:
                    # 解析JSON内容
                    analysis_json = json.loads(analysis_content)
                    
                    logger.info(f"成功分析试卷")
                    return {
                        "status": "ok", 
                        "analysis": analysis_json,
                        "message": "试卷分析成功"
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"无法解析API返回的JSON: {str(e)}")
                    return {
                        "status": "error", 
                        "analysis": {},
                        "message": "API返回数据格式错误，无法解析JSON"
                    }
            else:
                logger.warning(f"API响应格式异常: {result}")
                return {
                    "status": "error", 
                    "analysis": {},
                    "message": "API响应格式异常，无法获取分析结果"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {str(e)}")
            return {
                "status": "error", 
                "analysis": {},
                "message": f"API请求失败: {str(e)}"
            }
        except json.JSONDecodeError:
            logger.error("API返回的不是有效的JSON格式")
            return {
                "status": "error", 
                "analysis": {},
                "message": "API返回格式错误"
            }
        except Exception as e:
            logger.error(f"分析试卷时发生未知错误: {str(e)}")
            traceback.print_exc()
            return {
                "status": "error", 
                "analysis": {},
                "message": f"试卷分析失败: {str(e)}"
            } 