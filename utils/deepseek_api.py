# -*- coding: utf-8 -*-
import os
import json
import requests
import logging
from typing import Dict, Any, Optional
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekAPI:
    """DeepSeek API封装类，用于调用DeepSeek AI大模型生成学生评语"""

    # API端点
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化DeepSeek API客户端
        
        Args:
            api_key: DeepSeek API密钥，如果不提供则从环境变量获取，如果环境变量也没有则使用默认值
        """
        # 默认API密钥 - 已更新为用户提供的密钥
        default_api_key = "sk-04f7d75638d044ed8a707d7aadf46782"
        
        # 检查传入的API密钥是否有效
        if api_key and api_key.strip():
            # 传入的API密钥有效
            self.api_key = api_key.strip()
            logger.info("使用自定义DeepSeek API密钥")
        elif os.environ.get("DEEPSEEK_API_KEY", "").strip():
            # 环境变量中的API密钥有效
            self.api_key = os.environ.get("DEEPSEEK_API_KEY").strip()
            logger.info("使用环境变量中的DeepSeek API密钥")
        else:
            # 使用默认API密钥
            self.api_key = default_api_key
            logger.info("使用默认DeepSeek API密钥")
            
        # 验证API密钥格式
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
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个简单的API测试助手。"},
                {"role": "user", "content": "返回'连接测试成功'这几个字，不要返回其他内容。"}
            ],
            "temperature": 0.1,
            "max_tokens": 10
        }
        
        try:
            # 发送请求
            logger.info("正在测试DeepSeek API连接...")
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()  # 检查HTTP错误
            
            # 解析响应
            result = response.json()
            
            # 检查响应是否包含预期字段
            if "choices" in result and len(result["choices"]) > 0:
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
                        max_length: int = 260) -> Dict[str, Any]:
        """生成学生评语
        
        Args:
            student_info: 学生信息，包含姓名、性别、特点、爱好等
            style: 评语风格，如"鼓励性的"、"严肃的"、"中肯的"等
            tone: 评语语气，如"正式的"、"亲切的"、"严厉的"等
            max_length: 评语最大字数
            
        Returns:
            包含生成评语的字典，格式为 {"status": "ok|error", "comment": "...", "message": "..."}
        """
        logger.info(f"开始为学生 {student_info.get('name')} 生成评语")
        logger.info(f"学生特征信息: 个性特点={student_info.get('personality', '未提供')}, 学习表现={student_info.get('study_performance', '未提供')}, 爱好={student_info.get('hobbies', '未提供')}, 待改进={student_info.get('improvement', '未提供')}")
        
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
评语应该是{style}和{tone}的。

学生信息:
- 姓名: {student_info.get('name', '学生')}
- 性别: {student_info.get('gender', '未知')}
- 个性特点: {student_info.get('personality', '未提供')}
- 学习表现: {student_info.get('study_performance', '未提供')}
- 课外活动/爱好: {student_info.get('hobbies', '未提供')}
- 需要改进的方面: {student_info.get('improvement', '未提供')}

请根据以上信息，生成一段全面、具体且有针对性的评语，突出{gender}的优点，同时也提出建设性的改进建议。

重要要求：
1. 评语的字数必须精确控制在不超过{max_length}个字，请在生成前仔细计算字数，确保不会超出限制
2. 不要生成超过{max_length}个字的评语然后截断，而是从一开始就精确控制好字数
3. 评语内容必须完整，不能因字数限制而出现不完整的句子
4. 确保评语内容积极向上且有指导意义
5. 必须高度个性化，根据提供的学生具体特点生成评语，避免千篇一律的模板化表达
6. 格式要求：不要在段落中间或段落之间添加空行；评语结尾不要添加字数统计信息；如果以"某某同学："开头，后面直接接正文，不要空行
7. 直接输出评语内容，不要添加任何标题、前缀或后缀
8. 绝对避免使用"春日里"、"像春日里的阳光"等常见模板化开头，每位学生的评语风格应该明显不同
9. 即使没有提供学生特征信息，每次生成的评语也应有明显差异，不要使用固定模式和表达方式
10. 使用多样化的表达方式和句式结构，根据学生的特点定制化表达

评语风格指南 - 根据选择的风格采用不同的表达方式：
- 如果是"鼓励性的"风格：使用温暖、积极的表达，强调进步空间和优点
- 如果是"严肃的"风格：使用更加正式、客观的陈述，直接指出问题和解决方案
- 如果是"中肯的"风格：保持平衡，客观评价优缺点，给出具体建议
- 如果是"温和的"风格：使用柔和的语言，委婉表达不足，重点表扬进步
- 如果是"诗意的"风格：【必须】在评语中引用至少一句完整的、与学生特点相关的古诗词名句或古文赋篇，并用引号标明。这是诗意风格最核心的要求，不可省略。评语整体应具有文学气息。
- 如果是"自然的"风格：如同日常对话，平实真诚，不做作不浮夸
"""

        # 根据是否提供了特征信息添加额外指导
        if has_personality or has_study_info or has_hobbies or has_improvement:
            prompt += "\n额外要求：\n"
            
            if has_personality:
                prompt += f"- 一定要突出学生的个性特点：\"{student_info.get('personality')}\"，并据此给出针对性评价\n"
            
            if has_study_info:
                prompt += f"- 评语中要明确反映学生的学习表现：\"{student_info.get('study_performance')}\"，并给予恰当评价\n"
            
            if has_hobbies:
                prompt += f"- 要提及并积极肯定学生的爱好特长：\"{student_info.get('hobbies')}\"\n"
            
            if has_improvement:
                prompt += f"- 对于学生需要改进的方面：\"{student_info.get('improvement')}\"，给予建设性且鼓励性的建议\n"
        else:
            # 如果没有提供特征信息，强调多样性和随机性
            prompt += """
特别注意：
- 由于没有提供详细的学生特征信息，请创造性地生成评语
- 每次生成的评语必须有明显差异，不使用固定模板
- 使用多样化的句式结构、表达方式和主题
- 避免使用"春日里"、"像阳光一样"等常见套路表达
- 生成的评语应根据选定的风格和语气而显著不同
"""

        # 特别强调诗意风格的要求
        if style == "诗意的":
            prompt += """
【诗意风格特别强调】
- 这是最重要的要求：必须在评语中引用至少一句与学生特点相关的完整古诗词名句
- 引用的古诗词必须用引号标明，并可以简单说明出处
- 请选择恰当的、能反映学生特点或品质的古诗词
- 评语的其他部分也应当保持文学性，与引用的诗词风格一致
- 这是判断生成质量的关键标准，请务必执行
"""

        # 添加额外指令和结束提示
        prompt += f"""
{additional_instructions}
不要在回复中写除了评语之外的任何内容。
"""

        # 记录最终生成的提示词
        logger.info(f"最终提示词: {prompt}")

        # 构建请求体
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一名专业的班主任，善于为学生撰写个性化、有启发性的评语。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.9,  # 增加温度，提高创造性
            "top_p": 0.98,       # 使用更高的top_p采样，增加多样性
            "presence_penalty": 0.6,  # 增加存在惩罚，减少重复
            "frequency_penalty": 0.6,  # 增加频率惩罚，减少常见表达的使用
            "max_tokens": max_length * 2  # 确保有足够的token来生成评语
        }
        
        # 诗意风格调整参数，降低temperature以保证更好地遵循指令
        if style == "诗意的":
            payload["temperature"] = 0.8
        
        try:
            # 发送请求
            logger.info(f"正在为学生 {student_info.get('name')} 发送API请求...")
            
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=25)
            logger.info(f"API响应状态码: {response.status_code}")
            
            # 检查HTTP错误
            response.raise_for_status()
            
            # 记录原始响应
            response_text = response.text
            logger.info(f"API原始响应: {response_text[:200]}...")
            
            # 解析响应
            result = response.json()
            logger.info(f"API响应解析为JSON: {str(result)[:200]}...")
            
            # 提取生成的评语
            if "choices" in result and len(result["choices"]) > 0:
                comment = result["choices"][0]["message"]["content"].strip()
                logger.info(f"成功提取评语: {comment[:50]}...")
                
                # 检查评语长度
                if len(comment) > max_length:
                    logger.warning(f"生成的评语长度超出限制: {len(comment)}/{max_length} 字")
                    # 优化截断过程，尽量保持完整句子
                    truncated = self._truncate_to_complete_sentence(comment, max_length)
                    
                    return {
                        "status": "ok", 
                        "comment": truncated,
                        "message": f"评语已生成，原文超出字数限制，已截断至 {len(truncated)} 字"
                    }
                
                logger.info(f"已成功生成评语，长度为 {len(comment)} 字")
                return {
                    "status": "ok", 
                    "comment": comment,
                    "message": "评语生成成功"
                }
            else:
                logger.error(f"API返回格式异常，无choices字段: {result}")
                return {
                    "status": "error",
                    "message": "评语生成失败: API返回格式异常，无法提取评语内容",
                    "comment": ""
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {str(e)}")
            return {
                "status": "error",
                "message": f"评语生成失败: API请求失败: {str(e)}",
                "comment": ""
            }
        except json.JSONDecodeError as e:
            logger.error(f"API返回的不是有效的JSON格式: {str(e)}")
            logger.error(f"原始响应: {response.text[:200]}...")
            return {
                "status": "error",
                "message": "评语生成失败: API返回格式错误，无法解析为JSON",
                "comment": ""
            }
        except Exception as e:
            logger.error(f"生成评语时发生未知错误: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"评语生成失败: {str(e)}",
                "comment": ""
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
                
        # 如果没有找到合适的标点符号，直接截断
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
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": f"你是一名专业的{subject}教师和教学分析专家，善于分析试卷数据并提供有针对性的教学建议。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
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
                analysis_content = result["choices"][0]["message"]["content"].strip()
                
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