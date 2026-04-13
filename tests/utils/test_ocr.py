"""测试OCR文字识别工具模块"""
import pytest
import io
from unittest.mock import Mock, patch, MagicMock
from src.phoenixframe.utils.ocr import OCRUtil


class TestOCRUtil:
    """测试OCR工具类"""
    
    def test_ocr_not_available_import_error(self):
        """测试OCR依赖不可用时的错误"""
        with patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', False):
            with pytest.raises(ImportError, match="OCR dependencies not installed"):
                OCRUtil()
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    def test_initialization_default(self, mock_pytesseract):
        """测试默认初始化"""
        ocr = OCRUtil()
        assert ocr.language == "eng"
        # 默认初始化不会调用tesseract_cmd设置
        # 只验证没有显式设置路径
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    def test_initialization_with_custom_path(self, mock_pytesseract):
        """测试自定义路径初始化"""
        custom_path = "/usr/bin/tesseract"
        ocr = OCRUtil(tesseract_path=custom_path, language="chi_sim")
        
        assert ocr.language == "chi_sim"
        assert mock_pytesseract.pytesseract.tesseract_cmd == custom_path
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_extract_text_from_file_path(self, mock_image, mock_pytesseract):
        """测试从文件路径提取文字"""
        # 模拟PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img
        
        # 模拟pytesseract返回
        mock_pytesseract.image_to_string.return_value = "  Hello World  "
        
        ocr = OCRUtil()
        result = ocr.extract_text_from_image("/path/to/image.png", preprocess=False)
        
        assert result == "Hello World"
        mock_image.open.assert_called_with("/path/to/image.png")
        mock_pytesseract.image_to_string.assert_called_with(
            mock_img, 
            config="-l eng --oem 3 --psm 6"
        )
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_extract_text_from_bytes(self, mock_image, mock_pytesseract):
        """测试从字节数据提取文字"""
        # 模拟PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img
        
        # 模拟pytesseract返回
        mock_pytesseract.image_to_string.return_value = "Text from bytes"
        
        ocr = OCRUtil()
        image_bytes = b"fake_image_data"
        result = ocr.extract_text_from_image(image_bytes, preprocess=False)
        
        assert result == "Text from bytes"
        # 验证使用BytesIO打开
        mock_image.open.assert_called()
        call_args = mock_image.open.call_args[0][0]
        assert isinstance(call_args, io.BytesIO)
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    def test_extract_text_from_pil_image(self, mock_pytesseract):
        """测试从PIL Image对象提取文字"""
        # 模拟PIL Image对象
        mock_img = Mock()
        
        # 模拟pytesseract返回
        mock_pytesseract.image_to_string.return_value = "Direct PIL image"
        
        ocr = OCRUtil()
        result = ocr.extract_text_from_image(mock_img, preprocess=False)
        
        assert result == "Direct PIL image"
        mock_pytesseract.image_to_string.assert_called_with(
            mock_img, 
            config="-l eng --oem 3 --psm 6"
        )
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_extract_text_with_preprocessing(self, mock_image, mock_pytesseract):
        """测试带预处理的文字提取"""
        # 模拟PIL Image
        mock_img = Mock()
        mock_processed_img = Mock()
        mock_image.open.return_value = mock_img
        
        # 模拟pytesseract返回
        mock_pytesseract.image_to_string.return_value = "Preprocessed text"
        
        ocr = OCRUtil()
        
        with patch.object(ocr, '_preprocess_image', return_value=mock_processed_img) as mock_preprocess:
            result = ocr.extract_text_from_image("/path/to/image.png", preprocess=True)
            
            assert result == "Preprocessed text"
            mock_preprocess.assert_called_once_with(mock_img)
            mock_pytesseract.image_to_string.assert_called_with(
                mock_processed_img, 
                config="-l eng --oem 3 --psm 6"
            )
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_extract_text_with_custom_config(self, mock_image, mock_pytesseract):
        """测试使用自定义配置提取文字"""
        # 模拟PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img
        
        # 模拟pytesseract返回
        mock_pytesseract.image_to_string.return_value = "Custom config text"
        
        ocr = OCRUtil()
        custom_config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        result = ocr.extract_text_from_image("/path/to/image.png", 
                                           preprocess=False, 
                                           config=custom_config)
        
        assert result == "Custom config text"
        mock_pytesseract.image_to_string.assert_called_with(
            mock_img, 
            config=custom_config
        )
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_extract_text_ocr_exception(self, mock_image, mock_pytesseract):
        """测试OCR异常处理"""
        # 模拟PIL Image
        mock_img = Mock()
        mock_processed_img = Mock()
        mock_image.open.return_value = mock_img

        # 模拟pytesseract抛出异常
        mock_pytesseract.image_to_string.side_effect = Exception("OCR error")

        ocr = OCRUtil()

        with patch.object(ocr, '_preprocess_image', return_value=mock_processed_img):
            with patch('builtins.print') as mock_print:
                result = ocr.extract_text_from_image("/path/to/image.png")

                assert result == ""
                mock_print.assert_called_with("OCR failed: OCR error")
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_extract_text_with_confidence_success(self, mock_image, mock_pytesseract):
        """测试成功提取文字和置信度"""
        # 模拟PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img
        
        # 模拟pytesseract返回的数据
        mock_data = {
            'text': ['', 'Hello', 'World', ''],
            'conf': [0, 95, 87, 0],
            'left': [0, 10, 50, 0],
            'top': [0, 5, 5, 0],
            'width': [0, 30, 35, 0],
            'height': [0, 20, 20, 0]
        }
        mock_pytesseract.image_to_data.return_value = mock_data
        mock_pytesseract.Output.DICT = "dict"
        
        ocr = OCRUtil()
        result = ocr.extract_text_with_confidence("/path/to/image.png", preprocess=False)
        
        expected = {
            'text': 'Hello World',
            'words': [
                {
                    'text': 'Hello',
                    'confidence': 95,
                    'bbox': {'x': 10, 'y': 5, 'width': 30, 'height': 20}
                },
                {
                    'text': 'World',
                    'confidence': 87,
                    'bbox': {'x': 50, 'y': 5, 'width': 35, 'height': 20}
                }
            ],
            'word_count': 2
        }
        
        assert result == expected
        mock_pytesseract.image_to_data.assert_called_with(
            mock_img,
            output_type="dict",
            config="-l eng"
        )
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_extract_text_with_confidence_exception(self, mock_image, mock_pytesseract):
        """测试提取文字和置信度时的异常处理"""
        # 模拟PIL Image
        mock_img = Mock()
        mock_processed_img = Mock()
        mock_image.open.return_value = mock_img

        # 模拟pytesseract抛出异常
        mock_pytesseract.image_to_data.side_effect = Exception("Data extraction error")

        ocr = OCRUtil()

        with patch.object(ocr, '_preprocess_image', return_value=mock_processed_img):
            with patch('builtins.print') as mock_print:
                result = ocr.extract_text_with_confidence("/path/to/image.png")

                expected = {'text': '', 'words': [], 'word_count': 0}
                assert result == expected
                mock_print.assert_called_with("OCR with confidence failed: Data extraction error")
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    def test_find_text_in_image_found(self):
        """测试在图像中找到指定文字"""
        ocr = OCRUtil()
        
        # 模拟extract_text_with_confidence的返回
        mock_result = {
            'words': [
                {
                    'text': 'Hello',
                    'confidence': 95,
                    'bbox': {'x': 10, 'y': 5, 'width': 30, 'height': 20}
                },
                {
                    'text': 'World',
                    'confidence': 87,
                    'bbox': {'x': 50, 'y': 5, 'width': 35, 'height': 20}
                }
            ]
        }
        
        with patch.object(ocr, 'extract_text_with_confidence', return_value=mock_result):
            result = ocr.find_text_in_image("/path/to/image.png", "hello")
            
            expected = {
                'found': True,
                'text': 'Hello',
                'confidence': 95,
                'bbox': {'x': 10, 'y': 5, 'width': 30, 'height': 20}
            }
            assert result == expected
    
    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    def test_find_text_in_image_not_found(self):
        """测试在图像中未找到指定文字"""
        ocr = OCRUtil()
        
        # 模拟extract_text_with_confidence的返回
        mock_result = {
            'words': [
                {
                    'text': 'Hello',
                    'confidence': 95,
                    'bbox': {'x': 10, 'y': 5, 'width': 30, 'height': 20}
                }
            ]
        }
        
        with patch.object(ocr, 'extract_text_with_confidence', return_value=mock_result):
            result = ocr.find_text_in_image("/path/to/image.png", "goodbye")

            assert result is None

    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.cv2')
    @patch('src.phoenixframe.utils.ocr.np')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_preprocess_image(self, mock_image, mock_np, mock_cv2):
        """测试图像预处理"""
        # 模拟输入图像
        mock_input_image = Mock()

        # 模拟numpy数组转换
        mock_np_array = Mock()
        mock_np.array.return_value = mock_np_array

        # 模拟OpenCV操作
        mock_opencv_image = Mock()
        mock_gray = Mock()
        mock_blurred = Mock()
        mock_thresh = Mock()
        mock_processed1 = Mock()
        mock_processed2 = Mock()

        mock_cv2.cvtColor.side_effect = [mock_opencv_image, mock_gray]
        mock_cv2.GaussianBlur.return_value = mock_blurred
        mock_cv2.threshold.return_value = (None, mock_thresh)
        mock_cv2.morphologyEx.side_effect = [mock_processed1, mock_processed2]
        mock_cv2.MORPH_CLOSE = "close"
        mock_cv2.MORPH_OPEN = "open"
        mock_cv2.THRESH_BINARY = 1
        mock_cv2.THRESH_OTSU = 2

        # 模拟kernel创建
        mock_kernel = Mock()
        mock_np.ones.return_value = mock_kernel
        mock_np.uint8 = "uint8"

        # 模拟最终图像
        mock_final_image = Mock()
        mock_image.fromarray.return_value = mock_final_image

        ocr = OCRUtil()
        result = ocr._preprocess_image(mock_input_image)

        # 验证处理步骤
        mock_np.array.assert_called_with(mock_input_image)
        assert mock_cv2.cvtColor.call_count == 2  # RGB2BGR and BGR2GRAY
        mock_cv2.GaussianBlur.assert_called_with(mock_gray, (5, 5), 0)
        mock_cv2.threshold.assert_called_with(mock_blurred, 0, 255, 3)  # BINARY + OTSU
        mock_np.ones.assert_called_with((1, 1), "uint8")
        assert mock_cv2.morphologyEx.call_count == 2
        mock_image.fromarray.assert_called_with(mock_processed2)

        assert result == mock_final_image

    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_extract_numbers_only_success(self, mock_image, mock_pytesseract):
        """测试成功提取数字"""
        # 模拟PIL Image
        mock_img = Mock()
        mock_processed_img = Mock()
        mock_image.open.return_value = mock_img

        # 模拟pytesseract返回
        mock_pytesseract.image_to_string.return_value = "  12345  "

        ocr = OCRUtil()

        with patch.object(ocr, '_preprocess_image', return_value=mock_processed_img):
            result = ocr.extract_numbers_only("/path/to/image.png")

            assert result == "12345"
            mock_pytesseract.image_to_string.assert_called_with(
                mock_processed_img,
                config="-l eng --oem 3 --psm 8 -c tessedit_char_whitelist=0123456789"
            )

    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_extract_numbers_only_no_preprocessing(self, mock_image, mock_pytesseract):
        """测试不预处理提取数字"""
        # 模拟PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img

        # 模拟pytesseract返回
        mock_pytesseract.image_to_string.return_value = "67890"

        ocr = OCRUtil()
        result = ocr.extract_numbers_only("/path/to/image.png", preprocess=False)

        assert result == "67890"
        mock_pytesseract.image_to_string.assert_called_with(
            mock_img,
            config="-l eng --oem 3 --psm 8 -c tessedit_char_whitelist=0123456789"
        )

    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_extract_numbers_only_from_bytes(self, mock_image, mock_pytesseract):
        """测试从字节数据提取数字"""
        # 模拟PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img

        # 模拟pytesseract返回
        mock_pytesseract.image_to_string.return_value = "999"

        ocr = OCRUtil()
        image_bytes = b"fake_image_data"
        result = ocr.extract_numbers_only(image_bytes, preprocess=False)

        assert result == "999"
        # 验证使用BytesIO打开
        mock_image.open.assert_called()
        call_args = mock_image.open.call_args[0][0]
        assert isinstance(call_args, io.BytesIO)

    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    def test_extract_numbers_only_from_pil_image(self, mock_pytesseract):
        """测试从PIL Image对象提取数字"""
        # 模拟PIL Image对象
        mock_img = Mock()

        # 模拟pytesseract返回
        mock_pytesseract.image_to_string.return_value = "123"

        ocr = OCRUtil()
        result = ocr.extract_numbers_only(mock_img, preprocess=False)

        assert result == "123"
        mock_pytesseract.image_to_string.assert_called_with(
            mock_img,
            config="-l eng --oem 3 --psm 8 -c tessedit_char_whitelist=0123456789"
        )

    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    @patch('src.phoenixframe.utils.ocr.pytesseract')
    @patch('src.phoenixframe.utils.ocr.Image')
    def test_extract_numbers_only_exception(self, mock_image, mock_pytesseract):
        """测试提取数字时的异常处理"""
        # 模拟PIL Image
        mock_img = Mock()
        mock_processed_img = Mock()
        mock_image.open.return_value = mock_img

        # 模拟pytesseract抛出异常
        mock_pytesseract.image_to_string.side_effect = Exception("Number extraction error")

        ocr = OCRUtil()

        with patch.object(ocr, '_preprocess_image', return_value=mock_processed_img):
            with patch('builtins.print') as mock_print:
                result = ocr.extract_numbers_only("/path/to/image.png")

                assert result == ""
                mock_print.assert_called_with("Number extraction failed: Number extraction error")

    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    def test_is_text_present_found_high_confidence(self):
        """测试检查文字存在（高置信度）"""
        ocr = OCRUtil()

        # 模拟extract_text_with_confidence的返回
        mock_result = {
            'words': [
                {
                    'text': 'Hello',
                    'confidence': 95
                },
                {
                    'text': 'World',
                    'confidence': 60
                }
            ]
        }

        with patch.object(ocr, 'extract_text_with_confidence', return_value=mock_result):
            result = ocr.is_text_present("/path/to/image.png", "hello", min_confidence=50)
            assert result is True

    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    def test_is_text_present_found_low_confidence(self):
        """测试检查文字存在（低置信度）"""
        ocr = OCRUtil()

        # 模拟extract_text_with_confidence的返回
        mock_result = {
            'words': [
                {
                    'text': 'Hello',
                    'confidence': 30  # 低于最小置信度
                }
            ]
        }

        with patch.object(ocr, 'extract_text_with_confidence', return_value=mock_result):
            result = ocr.is_text_present("/path/to/image.png", "hello", min_confidence=50)
            assert result is False

    @patch('src.phoenixframe.utils.ocr.OCR_AVAILABLE', True)
    def test_is_text_present_not_found(self):
        """测试检查文字不存在"""
        ocr = OCRUtil()

        # 模拟extract_text_with_confidence的返回
        mock_result = {
            'words': [
                {
                    'text': 'Hello',
                    'confidence': 95
                }
            ]
        }

        with patch.object(ocr, 'extract_text_with_confidence', return_value=mock_result):
            result = ocr.is_text_present("/path/to/image.png", "goodbye", min_confidence=50)
            assert result is False
