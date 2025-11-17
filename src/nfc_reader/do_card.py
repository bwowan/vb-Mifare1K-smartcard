import sys
import threading
import smartcard.util
import smartcard.System
from enum                      import Enum
from smartcard.CardRequest     import CardRequest
from smartcard.CardMonitoring  import CardMonitor, CardObserver
from smartcard.ATR             import ATR

#import time
#from smartcard.CardType        import CardType
#from smartcard.pcsc.PCSCReader import PCSCReader
#from smartcard.CardType        import AnyCardType
#from smartcard.CardConnection  import CardConnection


MIFARE_1K_blocks_per_sector = 4
MIFARE_1K_total_sectors     = 16
MIFARE_1K_bytes_per_block   = 16
MIFARE_1K_bytes_per_key     = 6
MIFARE_1K_default_key       = [0xFF for _ in range(MIFARE_1K_bytes_per_key)] 

def bytes2str(b):
    s = ""
    for i,ch in enumerate(b):
        s += f"{ch:02X}"
        if (i + 1 < len(b)):
            s += " "
    return "["+s+"]"
    
class status(Enum):
    NOINIT     = "NO INIT"
    OK         = "OK"
    NOT_READ   = "NOT READ"
    AUTH_ERROR = "AUTH ERROR"
    READ_ERROR = "READ ERROR"
    WRITE_ERROR= "WRITE ERROR"
    KEY_ERROR  = "KEY ERROR"
    NO_READERS = "NO READERS"

def parseAccessBits(b6, b7):
    b6 ^= 0xFF #C23│C22│C21│C20│C13│C12│C11│C10 (7-1)
    b7 ^= 0xFF #C33│C32│C31│C30│C23│C22│C21│C20
    #b8 ^= 0xFF #~C13│~C12│~C11│~C10│~C33│~C32│~C31│~C30│ it's checking byte that duplicate info
    blockAcess=bytearray(MIFARE_1K_blocks_per_sector)
    blockAcess[0] = ( (b6       & 0x01)  << 2) | ( (b7       & 0x01) < 1) | ((b7 >> 4) & 0x01)
    blockAcess[1] = (((b6 >> 1) & 0x01)  << 2) | (((b7 >> 1) & 0x01) < 1) | ((b7 >> 5) & 0x01)
    blockAcess[2] = (((b6 >> 2) & 0x01)  << 2) | (((b7 >> 2) & 0x01) < 1) | ((b7 >> 6) & 0x01)
    blockAcess[3] = (((b6 >> 3) & 0x01)  << 2) | (((b7 >> 3) & 0x01) < 1) | ((b7 >> 7) & 0x01)
    return blockAcess
    
bitAccessMap = {
    0b000: "R(A,B) W(A,B) I(A,B) D(A,B)",
    0b001: "R(A,B) W(B,B) I(-) D(-)",
    0b010: "R(A,B) W(B) I(A,B) D(A,B)",
    0b011: "R(B) W(B) I(-) D(-)",
    0b100: "R(A,B) W(B) I(A,B) D(A,B)",
    0b101: "R(B) W(-) I(-,B) D(-,B)",
    0b110: "R(A,B) W(-,B) I(-) D(-)",
    0b111: "R(A,B) W(-) I(-) D(-)"
} 

def accessBitsToStr(accessBytes):
    blockAcess = parseAccessBits(accessBytes[0], accessBytes[1])
    resultStrBlocks = [""  for _ in range(MIFARE_1K_blocks_per_sector)]
    for i in range(MIFARE_1K_blocks_per_sector):
        resultStrBlocks[i] = bitAccessMap.get(blockAcess[i])
    return resultStrBlocks  


#full dump data for Mifare 1k card
class dumpMifare_1k:
    #data of each block
    class block:            
        def __init__(self):
            self.data   = bytearray(MIFARE_1K_bytes_per_block)
            self.status = status.NOINIT

    #data of block 0 of secor 0
    class head:
        def __init__(self):
            self.UID  = bytearray(4)  #(0-3) first 4 bytes (unique ID of card)
            self.BCC  = 0x00          #(4-4) 4th byte (ecc of UID)
            self.SAK  = bytearray(3)  #(5-7) bytes of block 0 (fabricant data)
            self.SIGN = bytearray(8)  #(7-15)last 8 bytes (sign of manufacturer)

        def read(self, block):
            if block.status == status.OK:
                self.UID  = block.data[0:4]
                self.BCC  = block.data[4]
                self.SAK  = block.data[5:8]
                self.SIGN = block.data[8:16]
        
        def toStr(self):
            return f"UID:{bytes2str(self.UID)} BCC[0x{self.BCC:02X}] SAK:{bytes2str(self.SAK)} SIGN:{bytes2str(self.SIGN)}"

    #data of trailer block (3) of each sector
    class trailer:
        def __init__(self):
            self.keyA       = MIFARE_1K_default_key #default key for many cards
            self.keyB       = MIFARE_1K_default_key #default key for many cards
            self.accessBits = bytearray(3)
            self.GPB        = 0x00                  #General Purpose Byte
            self.status     = status.NOINIT
            
        def processLastBlock(self, data):
            #self.keyA      = data[0:6] #always zero, keyA is unreadable
            self.accessBits = data[6:9]
            self.GPB        = data[9]
            self.keyB       = data[10:16]
            self.status     = status.OK
        
        def toStr(self):
            return f"KeyB: {bytes2str(self.keyB)} GPB:{self.GPB:02X} AccessBits:{bytes2str(self.accessBits)}"

    #data of entire sector     
    class sector:
        def __init__(self):
            self.blocks  = [dumpMifare_1k.block() for _ in range(MIFARE_1K_blocks_per_sector)]
            self.trailer = dumpMifare_1k.trailer()
            self.status  = status.NOINIT
    
    def __init__(self):
        self.head    = dumpMifare_1k.head()
        self.sectors = [dumpMifare_1k.sector() for _ in range(MIFARE_1K_total_sectors)]
        self.status  = status.NOINIT
        
#send request to card
def doTransmit(connection, Key):
    try:
        response, sw1, sw2 = connection.transmit(Key)
        if (sw1 == 0x90) and (sw2 == 0x00):
            return True, response
    except Exception as e:
        print(f"transmit error: {e}")
    return False

#print all read info
def printDump(dump, firstSectorOnly = True, fullData = True):
    print(dump.head.toStr())
    for iSector, sector in enumerate(dump.sectors):
        print(f"sector {iSector:02d} {sector.status.value}; {sector.trailer.toStr()}")
        accessBitsStr = accessBitsToStr(sector.trailer.accessBits)
        if fullData:
            for iBlock, block in enumerate(sector.blocks):
                s = f" {iBlock:02d} {block.status.value}"
                if block.status == status.OK:
                    if fullData:
                        s += f" {smartcard.util.toHexString(block.data)}"
                    s += f" access: {accessBitsStr[iBlock]}"
                print(s)
        if (firstSectorOnly):
            break
    return

#read all card info
def dump_mifare_1k(dump, connection, firstSectorOnly=True, keyA = MIFARE_1K_default_key):
    try:
        totalFailCount = 0
        for iSector, sector in enumerate(dump.sectors):
            nBlock0 = iSector * 4
            # load key A (default)
            if not doTransmit(connection, [0xFF, 0x82, 0x00, 0x00, 0x06] + keyA):
                sector.status = status.KEY_ERROR
                totalFailCount += 1
            else:
                # auntificate by key A
                if not doTransmit(connection, [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, nBlock0, 0x60, 0x00]):
                    sector.status = status.AUTH_ERROR
                    totalFailCount += 1
                else:
                    failCount = 0
                    sector.status = status.OK
                    for iBlock, block in enumerate(sector.blocks):
                        readOk, data = doTransmit(connection, [0xFF, 0xB0, 0x00, nBlock0 + iBlock, 0x10])
                        if readOk:
                            block.data = data
                            block.status = status.OK
                            if (iBlock + 1) == MIFARE_1K_blocks_per_sector:
                                sector.trailer.processLastBlock(block.data)   
                        else:
                            failCount += 1
                            totalFailCount += 1
                            block.status = status.READ_ERROR
                    if failCount != 0:
                        sector.status = status.READ_ERROR
            if firstSectorOnly: #read only first block of first sector
                break
                        
        dump.head.read(dump.sectors[0].blocks[0])
    except Exception as e:
        dump.status = status.READ_ERROR
        print(f"dump error: {e}")
    return

        
#=================================
def sendRequest(firstSectorOnly=True):
    crdRequest = CardRequest(timeout=10)
    crdService = crdRequest.waitforcard()
    try:
        connection=crdService.connection
        connection.connect(mode=smartcard.scard.SCARD_SHARE_EXCLUSIVE, disposition=smartcard.scard.SCARD_UNPOWER_CARD)
        #atr = ATR(connection.getATR())
        #atr.dump();
        dump = dumpMifare_1k()
        dump.reader = readers[0].name
        dump_mifare_1k(dump, connection, firstSectorOnly) 
        printDump(dump, firstSectorOnly)
    except Exception as e:
        print (f"{e}")
    finally:
        connection.disconnect()


class PrintObserver(CardObserver):
    def __init__(self):
        self.processedEvent =  threading.Event()

    def update(self, observable, handlers):
        if len(handlers[0]) != 0:
            print("\rInserted: ", bytes2str(handlers[0][0].atr))
            sendRequest()
            self.processedEvent.set()
            

def observerThread(observer):
    monitor = CardMonitor()
    monitor.addObserver(observer)
    try:
        n = 12
        while n > 0 and not observer.processedEvent.is_set():
            n -= 1
            sys.stdout.write(f"\rwaiting for card {n:02d}")
            observer.processedEvent.wait(timeout=1)
    finally:
        monitor.deleteObserver(observer)
        
def startObserver():
    observer = PrintObserver()
    t = threading.Thread(target=observerThread, daemon=True, args=(observer,))
    t.start()
    t.join()
    if not observer.processedEvent.is_set():
        print("\rtimeout...                        ")


###################################################
if __name__ == "__main__":
    readers = smartcard.System.readers()
    if not readers:
        print("no readers")
    else:
        print(readers[0])
        #sendRequest()
        startObserver()
