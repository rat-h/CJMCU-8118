#
# CCS811_RPi
#
# Petr Lukas
# July, 11 2017
#
# Version 1.0

import struct, array, time, io, fcntl, logging

# I2C Address
CCS811_ADDRESS =  (0x5A)

# Registers
CCS811_HW_ID            =  (0x20)
CSS811_STATUS           =  (0x00)
CSS811_APP_START        =  (0xF4)
CSS811_MEAS_MODE        =  (0x01)
CSS811_ERROR_ID         =  (0xE0)
CSS811_RAW_DATA         =  (0x03)
CSS811_ALG_RESULT_DATA  =  (0x02)
CSS811_BASELINE         =  (0x11)
CSS811_ENV_DATA         =  (0x05)

# Errors ID
ERROR = {}
ERROR[0] = 'WRITE_REG_INVALID'
ERROR[1] = 'READ_REG_INVALID'
ERROR[2] = 'MEASMODE_INVALID'
ERROR[3] = 'MAX_RESISTANCE'
ERROR[4] = 'HEATER_FAULT'
ERROR[5] = 'HEATER_SUPPLY'

I2C_SLAVE=0x0703

#Max number of attempts to read/write I2C
MAXATT  = 10

#CCS811_fw, CCS811_fr = 0,0


class CCS811_RPi:
        def __init__(self, twi:int=1, addr:int=CCS811_ADDRESS, maxcnt:int=MAXATT ):
                self.addr      = addr
                self.twi       = twi
                self.cnt       = 0
                self.maxcnt    = maxcnt
                self._init_connection_()
        # helper functions
        def _init_connection_(self):
                self.CCS811_fr = io.open("/dev/i2c-"+str(self.twi), "rb", buffering=0)
                self.CCS811_fw = io.open("/dev/i2c-"+str(self.twi), "wb", buffering=0)

                # set device address
                fcntl.ioctl(self.CCS811_fr, I2C_SLAVE, self.addr)
                fcntl.ioctl(self.CCS811_fw, I2C_SLAVE, self.addr)
                time.sleep(0.015)
                self.cnt  += 1
                time.sleep(0.015)
                logging.info("Init/Reinit descriptors")

        def _write(self,s):
            if self.cnt >= self.maxcnt:
                logging.error("Exceed maximum number to attempt for reconnection")
                raise RuntimeError("CCS811_RPi:Exceed maximum number to attempt for reconnection")
            try:
                self.CCS811_fw.write( s )
            except:
                logging.error("Fail to write to the sensor")
                self._init_connection_()
                self._write(s)
            self.cnt = 0

        def _read(self,datasize):
            if self.cnt >= self.maxcnt:
                logging.error("Exceed maximum number to attempt for reconnection")
                raise RuntimeError("CCS811_RPi:Exceed maximum number to attempt for reconnection")
            try:
                data = self.CCS811_fr.read(datasize)
            except:
                logging.error("Fail to read the sensor")
                self._init_connection_()
                data = self._read(datasize)
            self.cnt = 0
            return data

        # public functions
        def checkHWID(self):
                s = [CCS811_HW_ID] # Hardware ID
                s2 = bytearray( s )
                self._write( s2 )
                time.sleep(0.0625)

                data = self._read(1)
       
                buf = array.array('B', data)
                return hex(buf[0])

        
        def readStatus(self):
                time.sleep(0.015)

                s = [CSS811_STATUS]
                s2 = bytearray( s )
                self._write( s2 )
                time.sleep(0.0625)              

                data = self._read(1)
                buf = array.array('B', data)
                return buf[0]

        def checkError(self,status_byte):
                time.sleep(0.015)
                error_bit = ((status_byte) >> 0) & 1
                if(not error_bit):
                        return False

                s = [CSS811_ERROR_ID]
                s2 = bytearray( s )
                self._write( s2 )
                time.sleep(0.0625)              

                data = self._read(1)
                buf = array.array('B', data)
                return ERROR[int(buf[0])]
        
        def configureSensor(self, configuration):
                # Switch sensor to application mode
                s = [CSS811_APP_START]
                s2 = bytearray( s )
                self._write( s2 )
                time.sleep(0.0625)

                s = [CSS811_MEAS_MODE,configuration,0x00]
                s2 = bytearray( s )
                self._write( s2 )
                time.sleep(0.015)
                return

        def readMeasMode(self):
                time.sleep(0.015)
                s = [CSS811_MEAS_MODE]
                s2 = bytearray( s )
                self._write( s2 )
                time.sleep(0.0625)              

                data = self._read(1)
                buf = array.array('B', data)
                return bin(buf[0])

        def readRaw(self):
                time.sleep(0.015)
                s = [CSS811_RAW_DATA]
                s2 = bytearray( s )
                self._write( s2 )
                time.sleep(0.0625)              

                data = self._read(2)
                buf = array.array('B', data)
                return (buf[0]*256 + buf[1])

        def readAlg(self):
                time.sleep(0.015)
                s = [CSS811_ALG_RESULT_DATA]
                s2 = bytearray( s )
                self._write( s2 )
                time.sleep(0.0625)              

                data = self._read(8)
                buf = array.array('B', data)
                result = {}
                # Read eCO2 value and check if it is valid
                result['eCO2'] = buf[0]*256 + buf[1]
                if(result['eCO2'] > 8192):
                        logging.error('Invalid eCO2 value')
                        #return False
                        result['eCO2'] = "ERROR"
                # Read TVOC value and check if it is valid
                result['TVOC'] = buf[2]*256 + buf[3]
                if(result['TVOC'] > 1187):
                        logging.error('Invalid TVOC value')
                        #return False
                        result['TVOC'] = "ERROR"
                
                result['status'] = buf[4]

                # Read the last error ID and check if it is valid
                result['errorid'] = buf[5]
                if(result['errorid'] > 5):
                        logging.error('Invalid Error ID')
                        return False
                        
                result['raw'] = buf[6]*256 + buf[7]
                return result

        def readBaseline(self):
                time.sleep(0.015)
                s = [CSS811_BASELINE]
                s2 = bytearray( s )
                self._write( s2 )
                time.sleep(0.0625)              

                data = self._read(2)
                buf = array.array('B', data)
                return (buf[0]*256 + buf[1])

        def checkDataReady(self, status_byte):
                ready_bit = ((status_byte) >> 3) & 1
                if(ready_bit):
                        return True
                else: return False

        def setCompensation(self, temperature, humidity):
                temperature = round(temperature,2)
                humidity = round(humidity,2)
                logging.debug(f'Setting compensation to {temperature}C and {humidity}%')
                hum1 = int(humidity//0.5)
                hum2 = int(humidity*512-hum1*256)

                temperature = temperature+25
                temp1 = int(temperature//0.5)
                temp2 = int(temperature*512-temp1*256)

                s = [CSS811_ENV_DATA,hum1,hum2,temp1,temp2,0x00]
                s2 = bytearray( s )
                self._write( s2 )
                
                return

        def setBaseline(self, baseline):
                loggin.info(f'Setting baseline to {baseline}')
                buf = [0,0]
                s = struct.pack('>H', baseline)
                buf[0], buf[1] = struct.unpack('>BB', s)
                loggin.info(f'{buf[0]}')
                loggin.info(f'{buf[1]}')
                
                s = [CSS811_BASELINE,buf[0],buf[1],0x00]
                s2 = bytearray( s )
                self._write( s2 )
                time.sleep(0.015)
