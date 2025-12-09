"""
Tests for do_prompt module.

This module tests user input functions, enum conversions, and data validation.
"""
import pytest
import threading
from unittest.mock import patch, MagicMock
import sys
import os
import io

# Import the module to test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nfc_reader.do_prompt import (
    actions,
    writeDatType,
    writeAddress,
    dataTypeFromStr,
    addressFromStr,
    PromptAnswer_ForWrite,
    fnInputString_FromTerminal_WithCancellation,
    getUserInput,
    askNumber_FromTerminal,
    askSectorNumber_FromTerminal,
    askBlockNumber_FromTerminal,
    askConfirmWrite_FromTerminal,
    askTextData_FromTerminal,
    askHexData_FromTerminal,
    fnAskWrite,
)


class TestEnumConversions:
    """Test enum conversion functions."""
    
    def test_dataTypeFromStr_default(self):
        """Test default return value for dataTypeFromStr."""
        assert dataTypeFromStr("") == writeDatType.W_STR
        assert dataTypeFromStr("abc") == writeDatType.W_STR
    
    def test_dataTypeFromStr_valid_values(self):
        """Test valid data type conversions."""
        assert dataTypeFromStr("1") == writeDatType.W_DATA
        assert dataTypeFromStr("3") == writeDatType.W_ZERO
        assert dataTypeFromStr("4") == writeDatType.W_RAND
    
    def test_addressFromStr_default(self):
        """Test default return value for addressFromStr."""
        assert addressFromStr("") == writeAddress.A_BLOCK
        assert addressFromStr("abc") == writeAddress.A_BLOCK
    
    def test_addressFromStr_valid_values(self):
        """Test valid address conversions."""
        assert addressFromStr("2") == writeAddress.A_SECTOR
        assert addressFromStr("3") == writeAddress.A_ALL


class TestPromptAnswer_ForWrite:
    """Test PromptAnswer_ForWrite class."""
    
    def test_init_default(self):
        """Test default initialization."""
        answer = PromptAnswer_ForWrite()
        assert answer.nSector == -1
        assert answer.nBlock == -1
        assert answer.dataType == writeDatType.W_DATA
        assert answer.address == writeAddress.A_BLOCK
        assert answer.data == bytearray(0)
    
    def test_init_with_params(self):
        """Test initialization with parameters."""
        answer = PromptAnswer_ForWrite(nSector=5, nBlock=2)
        assert answer.nSector == 5
        assert answer.nBlock == 2
        assert answer.dataType == writeDatType.W_DATA
        assert answer.address == writeAddress.A_BLOCK
        assert answer.data == bytearray(0)


class TestFnInputString_FromTerminal_WithCancellation:
    """Test fnInputString_FromTerminal_WithCancellation function."""
    
    def test_cancellation_with_event(self):
        """Test that function returns empty string when cancelEvent is set."""
        cancelEvent = threading.Event()
        cancelEvent.set()
        
        with patch('sys.stdout'):
            result = fnInputString_FromTerminal_WithCancellation("test: ", cancelEvent)
            assert result == ""
    
    @patch('sys.stdin.isatty', return_value=False)
    @patch('builtins.input', return_value="test input")
    def test_blocking_input_fallback(self, mock_input, mock_isatty):
        """Test fallback to blocking input when select doesn't work."""
        cancelEvent = threading.Event()
        
        with patch('sys.stdout'):
            result = fnInputString_FromTerminal_WithCancellation("test: ", cancelEvent)
            assert result == "test input"
            mock_input.assert_called_once()
    
    @patch('sys.stdin.isatty', return_value=True)
    @patch('select.select')
    def test_non_blocking_input(self, mock_select, mock_isatty):
        """Test non-blocking input with select."""
        cancelEvent = threading.Event()
        mock_select.return_value = ([sys.stdin], [], [])
        
        with patch('sys.stdin.readline', return_value="test input\n"):
            with patch('sys.stdout'):
                result = fnInputString_FromTerminal_WithCancellation("test: ", cancelEvent)
                assert result == "test input"
                mock_select.assert_called()


class TestGetUserInput:
    """Test getUserInput function."""
    
    @patch('nfc_reader.do_prompt.fnInputString_FromTerminal_WithCancellation')
    def test_valid_input(self, mock_input):
        """Test getUserInput with valid input."""
        mock_input.return_value = "1"
        cancelEvent = threading.Event()
        
        result = getUserInput("test: ", ['1', '2', '3'], cancelEvent)
        assert result == "1"
    
    @patch('nfc_reader.do_prompt.fnInputString_FromTerminal_WithCancellation')
    @patch('builtins.print')
    def test_invalid_input_retry(self, mock_print, mock_input):
        """Test getUserInput retries on invalid input."""
        mock_input.side_effect = ["invalid", "2"]
        cancelEvent = threading.Event()
        
        result = getUserInput("test: ", ['1', '2', '3'], cancelEvent)
        assert result == "2"
        assert mock_input.call_count == 2
        mock_print.assert_called()


class TestAskNumber_FromTerminal:
    """Test askNumber_FromTerminal function."""
    
    @patch('nfc_reader.do_prompt.getUserInput')
    def test_valid_number(self, mock_get_user_input):
        """Test askNumber_FromTerminal with valid number."""
        mock_get_user_input.return_value = "5"
        cancelEvent = threading.Event()
        
        success, value = askNumber_FromTerminal(0, 10, "Enter number", cancelEvent)
        assert success is True
        assert value == 5
    
    @patch('nfc_reader.do_prompt.getUserInput')
    def test_invalid_number(self, mock_get_user_input):
        """Test askNumber_FromTerminal with invalid number."""
        mock_get_user_input.return_value = "abc"
        cancelEvent = threading.Event()
        
        success, value = askNumber_FromTerminal(0, 10, "Enter number", cancelEvent)
        assert success is False
        assert value == -1
    
    @patch('nfc_reader.do_prompt.getUserInput')
    def test_empty_input(self, mock_get_user_input):
        """Test askNumber_FromTerminal with empty input."""
        mock_get_user_input.return_value = ""
        cancelEvent = threading.Event()
        
        success, value = askNumber_FromTerminal(0, 10, "Enter number", cancelEvent)
        assert success is False
        assert value == -1


class TestAskSectorNumber_FromTerminal:
    """Test askSectorNumber_FromTerminal function."""
    
    @patch('nfc_reader.do_prompt.askNumber_FromTerminal')
    def test_sector_number(self, mock_ask_number):
        """Test askSectorNumber_FromTerminal calls askNumber_FromTerminal correctly."""
        mock_ask_number.return_value = (True, 5)
        cancelEvent = threading.Event()
        
        success, sector = askSectorNumber_FromTerminal(16, cancelEvent)
        assert success is True
        assert sector == 5
        mock_ask_number.assert_called_once_with(0, 15, "Enter sector number", cancelEvent)


class TestAskBlockNumber_FromTerminal:
    """Test askBlockNumber_FromTerminal function."""
    
    @patch('nfc_reader.do_prompt.askNumber_FromTerminal')
    def test_block_number_sector_0(self, mock_ask_number):
        """Test askBlockNumber_FromTerminal for sector 0 (starts from 1)."""
        mock_ask_number.return_value = (True, 2)
        cancelEvent = threading.Event()
        
        success, block = askBlockNumber_FromTerminal(0, 4, cancelEvent)
        assert success is True
        assert block == 2
        mock_ask_number.assert_called_once_with(1, 2, "Enter block number", cancelEvent)
    
    @patch('nfc_reader.do_prompt.askNumber_FromTerminal')
    def test_block_number_sector_nonzero(self, mock_ask_number):
        """Test askBlockNumber_FromTerminal for non-zero sector (starts from 0)."""
        mock_ask_number.return_value = (True, 1)
        cancelEvent = threading.Event()
        
        success, block = askBlockNumber_FromTerminal(1, 4, cancelEvent)
        assert success is True
        assert block == 1
        mock_ask_number.assert_called_once_with(0, 2, "Enter block number", cancelEvent)


class TestAskConfirmWrite_FromTerminal:
    """Test askConfirmWrite_FromTerminal function."""
    
    @patch('nfc_reader.do_prompt.getUserInput')
    def test_confirm_yes(self, mock_get_user_input):
        """Test askConfirmWrite_FromTerminal with Yes."""
        mock_get_user_input.return_value = "Y"
        cancelEvent = threading.Event()
        
        result = askConfirmWrite_FromTerminal("Test prompt", cancelEvent)
        assert result is True
    
    @patch('nfc_reader.do_prompt.getUserInput')
    def test_confirm_no(self, mock_get_user_input):
        """Test askConfirmWrite_FromTerminal with No."""
        mock_get_user_input.return_value = "N"
        cancelEvent = threading.Event()
        
        result = askConfirmWrite_FromTerminal("Test prompt", cancelEvent)
        assert result is False


class TestAskTextData_FromTerminal:
    """Test askTextData_FromTerminal function."""
    
    @patch('nfc_reader.do_prompt.fnInputString_FromTerminal_WithCancellation')
    def test_text_data_with_padding(self, mock_input):
        """Test askTextData_FromTerminal pads data correctly."""
        mock_input.return_value = "hello"
        cancelEvent = threading.Event()
        
        result = askTextData_FromTerminal(16, cancelEvent)
        assert len(result) == 16
        assert result.startswith(b"hello")
        assert result.endswith(b" ")
    
    @patch('nfc_reader.do_prompt.fnInputString_FromTerminal_WithCancellation')
    @patch('builtins.print')
    def test_text_data_empty(self, mock_print, mock_input):
        """Test askTextData_FromTerminal with empty input."""
        mock_input.return_value = ""
        cancelEvent = threading.Event()
        
        result = askTextData_FromTerminal(16, cancelEvent)
        assert result == bytearray(0)
        mock_print.assert_called()


class TestAskHexData_FromTerminal:
    """Test askHexData_FromTerminal function."""
    
    @patch('nfc_reader.do_prompt.fnInputString_FromTerminal_WithCancellation')
    def test_hex_data_valid(self, mock_input):
        """Test askHexData_FromTerminal with valid hex data."""
        mock_input.return_value = "FF00AA"
        cancelEvent = threading.Event()
        
        result = askHexData_FromTerminal(16, cancelEvent)
        assert len(result) == 16
        assert result[:3] == bytearray([0xFF, 0x00, 0xAA])
        # Rest should be padding (zeros)
        assert all(b == 0 for b in result[3:])
    
    @patch('nfc_reader.do_prompt.fnInputString_FromTerminal_WithCancellation')
    @patch('builtins.print')
    def test_hex_data_invalid(self, mock_print, mock_input):
        """Test askHexData_FromTerminal with invalid hex data."""
        mock_input.side_effect = ["INVALID", ""]
        cancelEvent = threading.Event()
        
        result = askHexData_FromTerminal(16, cancelEvent)
        assert result == bytearray(0)
        mock_print.assert_called()
    
    @patch('nfc_reader.do_prompt.fnInputString_FromTerminal_WithCancellation')
    def test_hex_data_empty(self, mock_input):
        """Test askHexData_FromTerminal with empty input."""
        mock_input.return_value = ""
        cancelEvent = threading.Event()
        
        result = askHexData_FromTerminal(16, cancelEvent)
        assert result == bytearray(0)


class TestFnAskWrite:
    """Test fnAskWrite function."""
    
    @patch('nfc_reader.do_prompt.getUserInput')
    @patch('nfc_reader.do_prompt.askSectorNumber_FromTerminal')
    @patch('nfc_reader.do_prompt.askBlockNumber_FromTerminal')
    @patch('nfc_reader.do_prompt.askTextData_FromTerminal')
    @patch('builtins.print')
    def test_fnAskWrite_string_block(self, mock_print, mock_ask_text, mock_ask_block, 
                                      mock_ask_sector, mock_get_user_input):
        """Test fnAskWrite with string data type and block address."""
        mock_get_user_input.side_effect = ["", ""]  # Default selections
        mock_ask_sector.return_value = (True, 1)
        mock_ask_block.return_value = (True, 2)
        mock_ask_text.return_value = b"hello world     "
        cancelEvent = threading.Event()
        
        success, answer = fnAskWrite(16, 4, 16, cancelEvent)
        
        assert success is True
        assert answer.dataType == writeDatType.W_STR
        assert answer.address == writeAddress.A_BLOCK
        assert answer.nSector == 1
        assert answer.nBlock == 2
        assert answer.data == b"hello world     "
    
    @patch('nfc_reader.do_prompt.getUserInput')
    @patch('nfc_reader.do_prompt.askSectorNumber_FromTerminal')
    @patch('nfc_reader.do_prompt.askBlockNumber_FromTerminal')
    @patch('nfc_reader.do_prompt.askHexData_FromTerminal')
    @patch('builtins.print')
    def test_fnAskWrite_data_block(self, mock_print, mock_ask_hex, mock_ask_block, 
                                    mock_ask_sector, mock_get_user_input):
        """Test fnAskWrite with data type and block address."""
        mock_get_user_input.side_effect = ["1", ""]  # Data type, default address
        mock_ask_sector.return_value = (True, 2)
        mock_ask_block.return_value = (True, 1)  # Block number
        mock_ask_hex.return_value = bytearray([0xFF] * 16)
        cancelEvent = threading.Event()
        
        success, answer = fnAskWrite(16, 4, 16, cancelEvent)
        
        assert success is True
        assert answer.dataType == writeDatType.W_DATA
        assert answer.address == writeAddress.A_BLOCK
        assert answer.nSector == 2
        assert answer.nBlock == 1
    
    @patch('nfc_reader.do_prompt.getUserInput')
    @patch('nfc_reader.do_prompt.askConfirmWrite_FromTerminal')
    @patch('builtins.print')
    def test_fnAskWrite_zeros_all(self, mock_print, mock_confirm, mock_get_user_input):
        """Test fnAskWrite with zeros type and entire card address."""
        mock_get_user_input.side_effect = ["3", "3"]  # Zeros, entire card
        mock_confirm.return_value = True
        cancelEvent = threading.Event()
        
        success, answer = fnAskWrite(16, 4, 16, cancelEvent)
        
        assert success is True
        assert answer.dataType == writeDatType.W_ZERO
        assert answer.address == writeAddress.A_ALL
        assert len(answer.data) == 16 * 3 * 16  # nBlockSize * (nBlockCount - 1) * nSectorCount
    
    @patch('nfc_reader.do_prompt.getUserInput')
    @patch('nfc_reader.do_prompt.askSectorNumber_FromTerminal')
    @patch('builtins.print')
    def test_fnAskWrite_random_sector(self, mock_print, mock_ask_sector, mock_get_user_input):
        """Test fnAskWrite with random type and sector address."""
        mock_get_user_input.side_effect = ["4", "2"]  # Random, sector
        mock_ask_sector.return_value = (True, 5)
        cancelEvent = threading.Event()
        
        with patch('nfc_reader.do_prompt.askConfirmWrite_FromTerminal', return_value=True):
            success, answer = fnAskWrite(16, 4, 16, cancelEvent)
        
        assert success is True
        assert answer.dataType == writeDatType.W_RAND
        assert answer.address == writeAddress.A_SECTOR
        assert len(answer.data) == 16 * 3  # nBlockSize * (nBlockCount - 1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

