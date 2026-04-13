"""OCR文字识别工具模块"""
from typing import Optional, Dict, Any, Union
from pathlib import Path
import io

try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None
    Image = None
    cv2 = None
    np = None


class OCRUtil:
    """OCR文字识别工具类"""
    
    def __init__(self, tesseract_path: Optional[str] = None, language: str = "eng"):
        """
        初始化OCR工具
        
        Args:
            tesseract_path: Tesseract可执行文件路径
            language: 识别语言（eng, chi_sim, chi_tra等）
        """
        if not OCR_AVAILABLE:
            raise ImportError("OCR dependencies not installed. Please install: pip install pytesseract pillow opencv-python")
        
        self.language = language
        
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def extract_text_from_image(self, image_source: Union[str, bytes, Any], 
                               preprocess: bool = True,
                               config: Optional[str] = None) -> str:
        """
        从图像中提取文字
        
        Args:
            image_source: 图像源（文件路径、字节数据或PIL Image对象）
            preprocess: 是否预处理图像
            config: Tesseract配置参数
            
        Returns:
            str: 识别出的文字
        """
        # 加载图像
        if isinstance(image_source, str):
            # 文件路径
            image = Image.open(image_source)
        elif isinstance(image_source, bytes):
            # 字节数据
            image = Image.open(io.BytesIO(image_source))
        else:
            # PIL Image对象
            image = image_source
        
        # 预处理图像
        if preprocess:
            image = self._preprocess_image(image)
        
        # 设置配置
        if config is None:
            config = f"-l {self.language} --oem 3 --psm 6"
        
        # 执行OCR
        try:
            text = pytesseract.image_to_string(image, config=config)
            return text.strip()
        except Exception as e:
            print(f"OCR failed: {e}")
            return ""
    
    def extract_text_with_confidence(self, image_source: Union[str, bytes, Any],
                                   preprocess: bool = True) -> Dict[str, Any]:
        """
        从图像中提取文字并返回置信度信息
        
        Args:
            image_source: 图像源
            preprocess: 是否预处理图像
            
        Returns:
            Dict[str, Any]: 包含文字和置信度信息的字典
        """
        # 加载图像
        if isinstance(image_source, str):
            image = Image.open(image_source)
        elif isinstance(image_source, bytes):
            image = Image.open(io.BytesIO(image_source))
        else:
            image = image_source
        
        # 预处理图像
        if preprocess:
            image = self._preprocess_image(image)
        
        try:
            # 获取详细数据
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, 
                                           config=f"-l {self.language}")
            
            # 提取文字和置信度
            words = []
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:  # 过滤置信度为0的结果
                    words.append({
                        'text': data['text'][i],
                        'confidence': int(data['conf'][i]),
                        'bbox': {
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i]
                        }
                    })
            
            # 组合完整文字
            full_text = ' '.join([word['text'] for word in words if word['text'].strip()])
            
            return {
                'text': full_text,
                'words': words,
                'word_count': len(words)
            }
            
        except Exception as e:
            print(f"OCR with confidence failed: {e}")
            return {'text': '', 'words': [], 'word_count': 0}
    
    def find_text_in_image(self, image_source: Union[str, bytes, Any], 
                          target_text: str, 
                          preprocess: bool = True) -> Optional[Dict[str, Any]]:
        """
        在图像中查找指定文字的位置
        
        Args:
            image_source: 图像源
            target_text: 要查找的文字
            preprocess: 是否预处理图像
            
        Returns:
            Optional[Dict[str, Any]]: 文字位置信息，如果未找到返回None
        """
        result = self.extract_text_with_confidence(image_source, preprocess)
        
        for word in result['words']:
            if target_text.lower() in word['text'].lower():
                return {
                    'found': True,
                    'text': word['text'],
                    'confidence': word['confidence'],
                    'bbox': word['bbox']
                }
        
        return None
    
    def _preprocess_image(self, image: Any) -> Any:
        """
        预处理图像以提高OCR准确性
        
        Args:
            image: PIL Image对象
            
        Returns:
            Any: 预处理后的图像
        """
        # 转换为OpenCV格式
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # 转换为灰度图
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # 应用高斯模糊去噪
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 应用阈值处理
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 形态学操作去除噪点
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)
        
        # 转换回PIL格式
        return Image.fromarray(processed)
    
    def extract_numbers_only(self, image_source: Union[str, bytes, Any],
                           preprocess: bool = True) -> str:
        """
        只提取图像中的数字
        
        Args:
            image_source: 图像源
            preprocess: 是否预处理图像
            
        Returns:
            str: 识别出的数字
        """
        config = f"-l {self.language} --oem 3 --psm 8 -c tessedit_char_whitelist=0123456789"
        
        # 加载图像
        if isinstance(image_source, str):
            image = Image.open(image_source)
        elif isinstance(image_source, bytes):
            image = Image.open(io.BytesIO(image_source))
        else:
            image = image_source
        
        # 预处理图像
        if preprocess:
            image = self._preprocess_image(image)
        
        try:
            text = pytesseract.image_to_string(image, config=config)
            return text.strip()
        except Exception as e:
            print(f"Number extraction failed: {e}")
            return ""
    
    def is_text_present(self, image_source: Union[str, bytes, Any], 
                       target_text: str,
                       preprocess: bool = True,
                       min_confidence: int = 50) -> bool:
        """
        检查图像中是否存在指定文字
        
        Args:
            image_source: 图像源
            target_text: 要检查的文字
            preprocess: 是否预处理图像
            min_confidence: 最小置信度
            
        Returns:
            bool: 是否存在指定文字
        """
        result = self.extract_text_with_confidence(image_source, preprocess)
        
        for word in result['words']:
            if (target_text.lower() in word['text'].lower() and 
                word['confidence'] >= min_confidence):
                return True
        
        return False
