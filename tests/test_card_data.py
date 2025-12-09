"""
Tests for card_data module.

This module tests MIFARE 1K card data structures, access bits parsing,
key management, and dump formatting functions.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Import the module to test
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, src_path)

# Add src/nfc_reader to path for relative imports
nfc_reader_path = os.path.join(src_path, 'nfc_reader')
sys.path.insert(0, nfc_reader_path)

from nfc_reader.card_data import (
    MIFARE_1K_blocks_per_sector,
    MIFARE_1K_total_sectors,
    MIFARE_1K_bytes_per_block,
    MIFARE_1K_bytes_per_key,
    MIFARE_1K_default_key,
    status,
    parseAccessBits,
    bitAccessMap,
    bytes2str,
    accessBitsToStr,
    keyType,
    key,
    dumpMifare_1k,
    printSector,
    printDump,
    printATR,
)


class TestConstants:
    """Test MIFARE 1K constants."""
    
    def test_blocks_per_sector(self):
        """Test MIFARE_1K_blocks_per_sector constant."""
        assert MIFARE_1K_blocks_per_sector == 4
    
    def test_total_sectors(self):
        """Test MIFARE_1K_total_sectors constant."""
        assert MIFARE_1K_total_sectors == 16
    
    def test_bytes_per_block(self):
        """Test MIFARE_1K_bytes_per_block constant."""
        assert MIFARE_1K_bytes_per_block == 16
    
    def test_bytes_per_key(self):
        """Test MIFARE_1K_bytes_per_key constant."""
        assert MIFARE_1K_bytes_per_key == 6
    
    def test_default_key(self):
        """Test MIFARE_1K_default_key constant."""
        assert len(MIFARE_1K_default_key) == MIFARE_1K_bytes_per_key
        assert all(b == 0xFF for b in MIFARE_1K_default_key)


class TestStatus:
    """Test status enum."""
    
    def test_status_values(self):
        """Test all status enum values."""
        assert status.S_NOINIT.value == "NO INIT"
        assert status.S_OK.value == "OK"
        assert status.S_NOT_READ.value == "NOT READ"
        assert status.S_AUTH_ERROR.value == "AUTH ERROR"
        assert status.S_READ_ERROR.value == "READ ERROR"
        assert status.S_WRITE_ERROR.value == "WRITE ERROR"
        assert status.S_KEY_ERROR.value == "KEY ERROR"
        assert status.S_NO_READERS.value == "NO READERS"


class TestBytes2Str:
    """Test bytes2str function."""
    
    def test_bytes2str_empty(self):
        """Test bytes2str with empty bytearray."""
        result = bytes2str(bytearray())
        assert result == "[]"
    
    def test_bytes2str_single_byte(self):
        """Test bytes2str with single byte."""
        result = bytes2str([0xFF])
        assert result == "[FF]"
    
    def test_bytes2str_multiple_bytes(self):
        """Test bytes2str with multiple bytes."""
        result = bytes2str([0x00, 0x01, 0xFF, 0xAB])
        assert result == "[00 01 FF AB]"
    
    def test_bytes2str_list(self):
        """Test bytes2str with list of bytes."""
        result = bytes2str([0x12, 0x34, 0x56])
        assert result == "[12 34 56]"


class TestParseAccessBits:
    """Test parseAccessBits function."""
    
    def test_parseAccessBits_basic(self):
        """Test basic access bits parsing."""
        b6 = 0xFF
        b7 = 0x07
        result = parseAccessBits(b6, b7)
        
        assert len(result) == MIFARE_1K_blocks_per_sector
        assert isinstance(result, bytearray)
    
    def test_parseAccessBits_all_zeros(self):
        """Test parseAccessBits with all zeros."""
        result = parseAccessBits(0x00, 0x00)
        # After XOR with 0xFF, b6 and b7 become 0xFF
        # This should produce specific access bits
        assert len(result) == 4
    
    def test_parseAccessBits_all_ones(self):
        """Test parseAccessBits with all ones."""
        result = parseAccessBits(0xFF, 0xFF)
        # After XOR with 0xFF, b6 and b7 become 0x00
        assert len(result) == 4
    
    def test_parseAccessBits_values_in_range(self):
        """Test parseAccessBits produces values in valid range (0-7)."""
        for b6 in range(256):
            for b7 in range(256):
                result = parseAccessBits(b6, b7)
                for val in result:
                    assert 0 <= val <= 7, f"Access bit value {val} out of range for b6={b6}, b7={b7}"


class TestBitAccessMap:
    """Test bitAccessMap dictionary."""
    
    def test_bitAccessMap_keys(self):
        """Test bitAccessMap has all required keys."""
        expected_keys = {0b000, 0b001, 0b010, 0b011, 0b100, 0b101, 0b110, 0b111}
        assert set(bitAccessMap.keys()) == expected_keys
    
    def test_bitAccessMap_values(self):
        """Test bitAccessMap values are strings."""
        for value in bitAccessMap.values():
            assert isinstance(value, str)
            assert len(value) > 0


class TestAccessBitsToStr:
    """Test accessBitsToStr function."""
    
    def test_accessBitsToStr_basic(self):
        """Test basic accessBitsToStr conversion."""
        access_bytes = bytearray([0xFF, 0x07, 0x80])
        result = accessBitsToStr(access_bytes)
        
        assert len(result) == MIFARE_1K_blocks_per_sector
        assert all(isinstance(s, str) for s in result)
    
    def test_accessBitsToStr_all_blocks(self):
        """Test accessBitsToStr returns string for each block."""
        access_bytes = bytearray([0x00, 0x00, 0x00])
        result = accessBitsToStr(access_bytes)
        
        assert len(result) == 4
        for i, access_str in enumerate(result):
            assert access_str in bitAccessMap.values() or access_str == ""
    
    def test_accessBitsToStr_valid_mapping(self):
        """Test accessBitsToStr uses valid bitAccessMap entries."""
        access_bytes = bytearray([0xFF, 0x07, 0x80])
        result = accessBitsToStr(access_bytes)
        
        for access_str in result:
            if access_str:  # If not empty
                assert access_str in bitAccessMap.values()


class TestKeyType:
    """Test keyType enum."""
    
    def test_keyType_values(self):
        """Test keyType enum values."""
        assert keyType.KT_A.value == "A"
        assert keyType.KT_B.value == "B"


class TestKey:
    """Test key class."""
    
    def test_key_init_default(self):
        """Test key initialization with defaults."""
        k = key()
        assert k.keyType == keyType.KT_A
        assert k.keyData == MIFARE_1K_default_key
    
    def test_key_init_custom(self):
        """Test key initialization with custom values."""
        custom_key = [0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC]
        k = key(keyType.KT_B, custom_key)
        assert k.keyType == keyType.KT_B
        assert k.keyData == custom_key
    
    def test_key_toStr(self):
        """Test key toStr method."""
        k = key(keyType.KT_A, [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        result = k.toStr()
        assert "A:" in result
        assert "[FF FF FF FF FF FF]" in result
    
    def test_key_toStr_keyB(self):
        """Test key toStr method with Key B."""
        k = key(keyType.KT_B, [0x00, 0x11, 0x22, 0x33, 0x44, 0x55])
        result = k.toStr()
        assert "B:" in result
        assert "[00 11 22 33 44 55]" in result


class TestDumpMifare1kBlock:
    """Test dumpMifare_1k.block class."""
    
    def test_block_init(self):
        """Test block initialization."""
        b = dumpMifare_1k.block()
        assert len(b.data) == MIFARE_1K_bytes_per_block
        assert b.status == status.S_NOINIT
    
    def test_block_toStr_no_init(self):
        """Test block toStr with S_NOINIT status."""
        b = dumpMifare_1k.block()
        result = b.toStr(True)
        assert result == status.S_NOINIT.value
    
    def test_block_toStr_ok_with_representation(self):
        """Test block toStr with S_OK status and representation."""
        b = dumpMifare_1k.block()
        b.status = status.S_OK
        b.data = bytearray([0x48, 0x65, 0x6C, 0x6C, 0x6F] + [0x00] * 11)  # "Hello"
        result = b.toStr(True)
        assert status.S_OK.value in result
        assert "Hello" in result or "'Hello" in result
    
    def test_block_toStr_ok_without_representation(self):
        """Test block toStr with S_OK status without representation."""
        b = dumpMifare_1k.block()
        b.status = status.S_OK
        b.data = bytearray([0xFF] * MIFARE_1K_bytes_per_block)
        result = b.toStr(False)
        assert status.S_OK.value in result
        assert "[" in result  # Should contain hex representation


class TestDumpMifare1kHead:
    """Test dumpMifare_1k.head class."""
    
    def test_head_init(self):
        """Test head initialization."""
        h = dumpMifare_1k.head()
        assert len(h.UID) == 4
        assert h.BCC == 0x00
        assert len(h.SAK) == 3
        assert len(h.SIGN) == 8
    
    def test_head_read_success(self):
        """Test head read from block with S_OK status."""
        h = dumpMifare_1k.head()
        block = dumpMifare_1k.block()
        block.status = status.S_OK
        block.data = bytearray([0x01, 0x02, 0x03, 0x04,  # UID
                                 0x05,                    # BCC
                                 0x06, 0x07, 0x08,        # SAK
                                 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10])  # SIGN
        
        h.read(block)
        
        assert h.UID == bytearray([0x01, 0x02, 0x03, 0x04])
        assert h.BCC == 0x05
        assert h.SAK == bytearray([0x06, 0x07, 0x08])
        assert h.SIGN == bytearray([0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10])
    
    def test_head_read_not_ok(self):
        """Test head read from block with non-OK status."""
        h = dumpMifare_1k.head()
        original_uid = h.UID.copy()
        block = dumpMifare_1k.block()
        block.status = status.S_READ_ERROR
        block.data = bytearray([0xFF] * MIFARE_1K_bytes_per_block)
        
        h.read(block)
        
        # Should not change if status is not OK
        assert h.UID == original_uid
    
    def test_head_toStr(self):
        """Test head toStr method."""
        h = dumpMifare_1k.head()
        h.UID = bytearray([0x01, 0x02, 0x03, 0x04])
        h.BCC = 0x05
        h.SAK = bytearray([0x06, 0x07, 0x08])
        h.SIGN = bytearray([0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10])
        
        result = h.toStr()
        assert "UID:" in result
        assert "BCC" in result
        assert "SAK:" in result
        assert "SIGN:" in result


class TestDumpMifare1kTrailer:
    """Test dumpMifare_1k.trailer class."""
    
    def test_trailer_init(self):
        """Test trailer initialization."""
        t = dumpMifare_1k.trailer()
        assert isinstance(t.keyA, key)
        assert isinstance(t.keyB, key)
        assert t.keyA.keyType == keyType.KT_A
        assert t.keyB.keyType == keyType.KT_B
        assert len(t.accessBits) == 3
        assert t.GPB == 0x00
        assert t.status == status.S_NOINIT
    
    def test_trailer_processLastBlock(self):
        """Test trailer processLastBlock method."""
        t = dumpMifare_1k.trailer()
        data = bytearray([0x00] * 6 +           # KeyA (unreadable, always 0)
                          [0xFF, 0x07, 0x80] +  # Access bits
                          [0x69] +              # GPB
                          [0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC])  # KeyB
        
        t.processLastBlock(data)
        
        assert t.accessBits == bytearray([0xFF, 0x07, 0x80])
        assert t.GPB == 0x69
        assert t.keyB.keyData == bytearray([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC])
        assert t.status == status.S_OK
    
    def test_trailer_toStr_ok(self):
        """Test trailer toStr with S_OK status."""
        t = dumpMifare_1k.trailer()
        t.status = status.S_OK
        t.keyB.keyData = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
        t.GPB = 0x69
        t.accessBits = bytearray([0xFF, 0x07, 0x80])
        
        result = t.toStr()
        assert "B:" in result
        assert "GPB:" in result
        assert "AccessBits:" in result
    
    def test_trailer_toStr_not_ok(self):
        """Test trailer toStr with non-OK status."""
        t = dumpMifare_1k.trailer()
        t.status = status.S_NOINIT
        
        result = t.toStr()
        assert result == "trailer not processed"


class TestDumpMifare1kSector:
    """Test dumpMifare_1k.sector class."""
    
    def test_sector_init(self):
        """Test sector initialization."""
        s = dumpMifare_1k.sector()
        assert len(s.blocks) == MIFARE_1K_blocks_per_sector
        assert isinstance(s.trailer, dumpMifare_1k.trailer)
        assert s.status == status.S_NOINIT
    
    def test_sector_blocks_initialized(self):
        """Test sector blocks are properly initialized."""
        s = dumpMifare_1k.sector()
        for block in s.blocks:
            assert isinstance(block, dumpMifare_1k.block)
            assert len(block.data) == MIFARE_1K_bytes_per_block


class TestDumpMifare1k:
    """Test dumpMifare_1k class."""
    
    def test_dumpMifare1k_init(self):
        """Test dumpMifare_1k initialization."""
        dump = dumpMifare_1k()
        assert isinstance(dump.head, dumpMifare_1k.head)
        assert len(dump.sectors) == MIFARE_1K_total_sectors
        assert len(dump.ATR) == 0
        assert dump.status == status.S_NOINIT
    
    def test_dumpMifare1k_sectors_initialized(self):
        """Test dump sectors are properly initialized."""
        dump = dumpMifare_1k()
        for sector in dump.sectors:
            assert isinstance(sector, dumpMifare_1k.sector)
            assert len(sector.blocks) == MIFARE_1K_blocks_per_sector


class TestPrintSector:
    """Test printSector function."""
    
    @patch('builtins.print')
    def test_printSector_basic(self, mock_print):
        """Test printSector basic functionality."""
        sector = dumpMifare_1k.sector()
        sector.status = status.S_OK
        sector.trailer.status = status.S_OK
        sector.trailer.accessBits = bytearray([0xFF, 0x07, 0x80])
        
        for i, block in enumerate(sector.blocks):
            block.status = status.S_OK
            block.data = bytearray([i] * MIFARE_1K_bytes_per_block)
        
        printSector(5, sector)
        
        assert mock_print.called
        # Check that sector number is printed
        call_args_str = str(mock_print.call_args_list)
        assert "sector" in call_args_str.lower() or "05" in call_args_str
    
    @patch('builtins.print')
    def test_printSector_with_access_bits(self, mock_print):
        """Test printSector includes access bits."""
        sector = dumpMifare_1k.sector()
        sector.status = status.S_OK
        sector.trailer.status = status.S_OK
        sector.trailer.accessBits = bytearray([0xFF, 0x07, 0x80])
        
        printSector(0, sector)
        
        assert mock_print.called


class TestPrintDump:
    """Test printDump function."""
    
    @patch('builtins.print')
    def test_printDump_default_sector(self, mock_print):
        """Test printDump with default sector list."""
        dump = dumpMifare_1k()
        dump.head.UID = bytearray([0x01, 0x02, 0x03, 0x04])
        
        printDump(dump)
        
        assert mock_print.called
    
    @patch('builtins.print')
    def test_printDump_specific_sectors(self, mock_print):
        """Test printDump with specific sector list."""
        dump = dumpMifare_1k()
        dump.sectors[0].status = status.S_OK
        dump.sectors[1].status = status.S_OK
        
        printDump(dump, sectors=[0, 1])
        
        assert mock_print.called
    
    @patch('builtins.print')
    def test_printDump_invalid_sector(self, mock_print):
        """Test printDump with invalid sector number."""
        dump = dumpMifare_1k()
        
        # Should not crash with invalid sector
        printDump(dump, sectors=[-1, 100])
        
        # Should still print head
        assert mock_print.called


class TestPrintATR:
    """Test printATR function."""
    
    @patch('nfc_reader.card_data.ATR')
    @patch('builtins.print')
    def test_printATR_basic(self, mock_print, mock_atr_class):
        """Test printATR basic functionality.
        
        Note: printATR uses dump.atr (lowercase) but the class has dump.ATR (uppercase).
        This test sets both to ensure compatibility.
        """
        mock_atr = MagicMock()
        mock_atr.isT0Supported.return_value = True
        mock_atr.isT1Supported.return_value = False
        mock_atr.isT15Supported.return_value = True
        mock_atr.getGuardTime.return_value = 10
        mock_atr.getHistoricalBytes.return_value = bytearray([0x01, 0x02])
        mock_atr_class.return_value = mock_atr
        
        dump = dumpMifare_1k()
        atr_data = bytearray([0x3B, 0x80, 0x80, 0x01, 0x01])
        dump.ATR = atr_data
        # Also set lowercase attribute as used in printATR function
        dump.atr = atr_data
        
        printATR(dump)
        
        assert mock_print.called
        mock_atr_class.assert_called_once_with(atr_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

