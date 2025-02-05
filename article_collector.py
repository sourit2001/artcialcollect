import tkinter as tk
from tkinter import ttk, messagebox
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time

class ArticleCollector:
    def __init__(self, root):
        self.root = root
        self.root.title("文章收藏器")
        
        # 窗口最大化
        self.root.state('zoomed')
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置grid权重
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # URL输入框
        self.url_label = ttk.Label(self.main_frame, text="请输入文章网址:")
        self.url_label.grid(row=0, column=0, sticky=tk.W)
        
        self.url_entry = ttk.Entry(self.main_frame)
        self.url_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        # 获取按钮
        self.fetch_button = ttk.Button(self.main_frame, text="获取文章", command=self.fetch_and_translate)
        self.fetch_button.grid(row=0, column=2, padx=5)
        
        # 创建左右文本框
        self.left_frame = ttk.LabelFrame(self.main_frame, text="原文")
        self.left_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        self.right_frame = ttk.LabelFrame(self.main_frame, text="译文")
        self.right_frame.grid(row=1, column=3, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # 配置文本框权重
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(3, weight=1)
        
        # 创建文本框和滚动条
        self.left_text = self.create_text_widget(self.left_frame)
        self.right_text = self.create_text_widget(self.right_frame)
        
        # 初始化翻译器
        self.translator = GoogleTranslator(source='auto', target='zh-CN')

    def create_text_widget(self, parent):
        # 创建滚动条
        scrollbar = ttk.Scrollbar(parent)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建文本框
        text = tk.Text(
            parent,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            font=('Arial', 12)
        )
        text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 配置滚动条
        scrollbar.config(command=text.yview)
        
        # 配置文本样式
        text.tag_configure('title', 
            font=('Arial', 24, 'bold'),
            justify='center',
            spacing3=20
        )
        text.tag_configure('heading', 
            font=('Arial', 18, 'bold'),
            spacing3=15,
            spacing1=10
        )
        text.tag_configure('body', 
            font=('Arial', 13),
            spacing1=5,
            spacing2=3,
            spacing3=8
        )
        
        return text

    def translate_text(self, text):
        try:
            # 分段翻译，每段最多4000字符
            if len(text) > 4000:
                parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
                translated_parts = []
                
                for i, part in enumerate(parts):
                    # 更新进度
                    self.fetch_button['text'] = f"翻译中... {i+1}/{len(parts)}"
                    self.root.update()
                    
                    # 添加重试机制
                    for attempt in range(3):
                        try:
                            translated = self.translator.translate(text=part)
                            translated_parts.append(translated)
                            break
                        except Exception as e:
                            if attempt == 2:  # 最后一次尝试
                                raise e
                            time.sleep(1)  # 失败后等待
                    
                    time.sleep(0.5)  # 请求间隔
                    
                return '\n'.join(translated_parts)
            else:
                return self.translator.translate(text=text)
                    
        except Exception as e:
            raise Exception(f"翻译失败: {str(e)}")

    def fetch_and_translate(self):
        url = self.url_entry.get()
        try:
            # 禁用按钮
            self.fetch_button.configure(state='disabled')
            self.fetch_button['text'] = "处理中..."
            self.root.update()
            
            # 获取文章
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=5)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 清理无关内容
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # 清空显示区域
            self.left_text.delete(1.0, tk.END)
            self.right_text.delete(1.0, tk.END)
            
            # 查找文章内容
            article = (
                soup.find('article') or 
                soup.find('main') or 
                soup.find(class_=['post-content', 'article-content', 'entry-content']) or
                soup.find(id=['post-content', 'article-content', 'entry-content'])
            )
            
            if not article:
                article = soup
            
            if article:
                # 处理标题
                title = soup.find('h1')
                if title:
                    title_text = title.get_text().strip()
                    if title_text:
                        self.left_text.insert(tk.END, title_text + "\n\n", 'title')
                        translated_title = self.translate_text(title_text)
                        self.right_text.insert(tk.END, translated_title + "\n\n", 'title')
                
                # 收集所有段落
                paragraphs = []
                for element in article.find_all(['h2', 'h3', 'h4', 'p']):
                    text = element.get_text().strip()
                    if text and len(text) > 20:  # 忽略太短的文本
                        tag = 'heading' if element.name in ['h2', 'h3', 'h4'] else 'body'
                        paragraphs.append((text, tag))
                
                # 批量处理段落
                for i in range(0, len(paragraphs), 2):  # 每次处理2个段落
                    batch = paragraphs[i:i+2]
                    combined_text = '\n'.join(text for text, _ in batch)
                    
                    # 显示原文
                    for text, tag in batch:
                        self.left_text.insert(tk.END, text + "\n\n", tag)
                    
                    # 翻译
                    try:
                        self.fetch_button['text'] = f"翻译中... {i//2 + 1}/{(len(paragraphs)+1)//2}"
                        self.root.update()
                        
                        translated = self.translate_text(combined_text)
                        translated_parts = translated.split('\n')
                        
                        # 显示译文
                        for (_, tag), trans_text in zip(batch, translated_parts):
                            self.right_text.insert(tk.END, trans_text + "\n\n", tag)
                            
                        self.right_text.update()
                        time.sleep(0.5)  # 避免请求过快
                    except Exception as e:
                        for text, tag in batch:
                            self.right_text.insert(tk.END, f"[翻译失败: {str(e)}]\n{text}\n\n", tag)
            else:
                raise Exception("无法找到文章内容")
                
        except Exception as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")
            
        finally:
            # 恢复按钮状态
            self.fetch_button.configure(state='normal')
            self.fetch_button['text'] = "获取文章"
            self.root.update()

if __name__ == "__main__":
    root = tk.Tk()
    app = ArticleCollector(root)
    root.mainloop()