#!/usr/bin/python
#coding=utf-8

#import MySQLdb
import MySQLdb.cursors
import datetime
from subprocess import * 
#from time import sleep, strftime
import time

import threading as _threading
import copy


from Adafruit_CharLCD import Adafruit_CharLCD

 
from DataAccess import DataAccessConnectionManager as dcmanager 


#cmd = "ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1"
cmd = "echo `hostname`"


def run_cmd(cmd):
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.communicate()[0]
    return output

DEBUG_LEVEL = 0


class DataTestor:
    def __init__(self, callback = None, logger = None):
        
        self.callback = callback        # 用于通知连接更新的回调函数注册，简化，唯一
                                        # 本例暂时不实现callback
        if logger == None:
            self.logger = self
        else:
            self.logger = logger
        
        self.dcmanager = dcmanager(self.callback_update_conn, self.logger)

        # 确定当前的时间
        self.current_date = datetime.datetime.now()
        self.delta_date = self.current_date - datetime.timedelta(days = 7)


        self.ready_input = True # 系统允许记录扫描条码时的标志
        self.barcode = ''       # 用来提供有效条码数据记录的变量

        barcode_watcher = _threading.Thread(target=self.barcode_watcher)
        barcode_watcher.start()        


    #===========================================================================
    # logwrite
    #===========================================================================
    def logwrite(self, loglevel, msg):
        if DEBUG_LEVEL >= loglevel :
            print __name__ 
            print loglevel, 
            for item in msg:
                print item,
            print 
            

    def callback_update_conn(self, cname):
        _conn = self.dcmanager.GetConnectByName(cname)
        if _conn == None:
            connstate = False
        else:
            connstate = True


    def __del__ (self):
        try:
            #self.conn.close()
            pass
        except :
            pass 

    def closedb(self):
        self.dcmanager.WatcherCanExit = True
        # 在主程序关闭以后，logger设置为自身函数
        #self.dcmanager.logger = self.dcmanager
        
        # 查询线程数据，直到获得可退出的信号
        if self.dcmanager.CanExit() == True:
            return True
        else:
            return False
 

    def check_conn_state(self, func_name):
        conndict = {'get_view_autoexec_by_sn': 'conn',
                    'get_view_failed_test_item' : 'conn',
                    'get_exist_box_item' : 'conn_tar',
                    'update_exist_box_state' : 'conn_tar',
                    'get_view_succeeded_one_item_test' : 'conn',
                    'add_new_packcge' : 'conn_tar',
                    'add_new_pkg_detail' : 'conn_tar',
                    'add_error_info': 'conn_tar', 
                    'obsolete_box_number': 'conn_tar', 
                    'insert_new_aging_record': 'conn_tar',
                    'insert_new_meter_sn_relation': 'conn_tar',
                    }
        cname = conndict.get(func_name)
        conn = self.dcmanager.GetConnectByName(cname)
        if conn == None:
            return None
        else:
            return conn
        
        
    def check_conn(self):
        fn = self
        def check_returns(self, * args, ** kwds):
            #print ' --check_conn--  ',fn.__name__ , args, kwds
            
            conn = self.check_conn_state(fn.__name__)
            
            if conn == None:    # 如果不能获取合法的数据库连接
                #print '直接返回空结果 '
                return {}
            else:
                #print '开始检索结果..........'
                kwds ['conn'] = conn
                #print args , kwds
                try:
                    result = fn(self, * args, ** kwds)
                except IOError, ex: #Exception, ex:
                    #print '出错', ex
                    result = {}
                return  result
        return  check_returns


    #===========================================================================
    # exec_query
    #===========================================================================
    @check_conn
    def get_view_autoexec_by_sn(self, sid, delta, bysmtid = 1, conn = None): 
        _delta_date = self.current_date - datetime.timedelta(days = delta)
        _str_delta_date = _delta_date.strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.cursor()

        # 按表号或者SMT序列号，查询该仪表的所有一键检测记录
        s=    """
            SELECT *
            FROM `view_autoexec_by_sn`
            WHERE 
            """
        if bysmtid == 0:
            s1 = """`meter_sn` = '%s'"""
        else:
            s1 = """`smt_sn` = '%s'"""
        s2 = """
            AND `op_time` > '%s'        
            ORDER BY `op_time` ASC,  
            `work_station_sn` ASC
            """
        qstring = s + s1 + s2 
        qstring = qstring % (sid, _str_delta_date)
        #print qstring
        _result = cursor.execute(qstring)
        dout = cursor.fetchall()
        return dout

    #===========================================================================
    # update_exist_box_state
    #===========================================================================
    @check_conn
    def update_exist_box_state(self, box_id, state, conn = None):
        qstring = """ 
        UPDATE `vehicle_meter_data`.`package_info` 
        SET `box_state` = '%s'
        WHERE `package_info`.`id` = %s  ;"""
        cursor = conn.cursor()

        qstring = qstring % (state, box_id)
        #print qstring 
        _result = cursor.execute(qstring)
        conn.commit()
        #dout = cursor.fetchall()
        return _result



    @check_conn
    def insert_new_aging_record(self, test_result, conn = None):
        cursor = conn.cursor()
        strsql="""INSERT INTO `vehicle_meter_data`.`meter_of_produce_index` (
        `tag` ,
        `insert_time` ,
        `produce_list_sn` ,
        `produce_type` ,
        `computer_name` ,
        `operator_number` ,
        `work_station_sn` ,
        `work_station_sum` ,
        `meter_status` ,
        `meter_sn` ,
        `op_time` ,
        `op_type` ,
        `op_overall_result`
        )
        VALUES (
        NULL ,
        CURRENT_TIMESTAMP , 
        '000', 
        '1', 
        %s, 
        '112', 
        '5', 
        '3', 
        '2', 
        %s, 
        %s, 
        '1', 
        '1'
        );
        """
        #print strsql % test_result
        cursor.execute(strsql, test_result)
        conn.commit()
        lastrowid = int(cursor.lastrowid)
        return lastrowid



# INSERT INTO `vehicle_meter_data`.`meter_sn_relation` (
# `stag` ,
# `ptag` ,
# `meter_sn` ,
# `smt_sn` ,
# `zb_sn` ,
# `sn1` ,
# `sn2`
# )
# VALUES (
# NULL , '1', '2', '3', '4', '5', '6'
# );
             
    @check_conn
    def insert_new_meter_sn_relation(self, test_result, conn = None):
        cursor = conn.cursor()
        strsql="""INSERT INTO `vehicle_meter_data`.`meter_sn_relation` (
            `stag` ,
            `ptag` ,
            `meter_sn` ,
            `smt_sn` ,
            `zb_sn` ,
            `sn1` ,
            `sn2`
            )
            VALUES (
            NULL , %s, %s, %s, '0', '0', '0'
            );
        """
        #print strsql % test_result
        cursor.execute(strsql, test_result)
        conn.commit()



    def barcode_watcher(self):
        self.isAlive = True
        while self.isAlive:
            #print 'ready for input:'
            barcode = raw_input('input:')
            #self.barQueue.put(barcode)
            if self.ready_input == True:
                self.barcode = barcode
            else:
                self.barcode = barcode = ''
            # time.sleep(0.3)
        pass

#===============================================================================
# 
#===============================================================================
if __name__ == "__main__":

    test = DataTestor()

#    import time
#    time.sleep(3)

#    rtval = test.get_view_autoexec_by_sn('116AA021401011645', 1000)
#    print 'rtval = ',rtval
#    for item in rtval:
#        print item
    

#    hostname = run_cmd(cmd)

#    kwds = dict(hostname = hostname[:-1], smtsn = '42901234567890')
#    print kwds
#    kwds = (hostname[:-1], '42901234567890')
#    test.insert_new_aging_record(kwds)
#    test.closedb()
    
        
    lcd = Adafruit_CharLCD()
    lcd.begin(16,1)
    
    _count = 200     # 单位延时100ms
    barcode = ''
    state = 0
    isworking = True
    
    dotindex = 3
    
    while isworking == True:
        
        if state == 0:    # 准备输入

            test.ready_input = True     #
            lcd.home()
            lcd.message('Ready for Scan: \n')
            
            if dotindex > (16 * 3):
                dotindex = 3
            if int(dotindex % 3) == 0:
                dot = '.'
                dot = dot.rjust(dotindex / 3).ljust(16)
                lcd.message(dot)
            dotindex += 1 

            if test.barcode != '':
                barcode = copy.copy(test.barcode)
                if barcode == 'WydTVEROJzowXQ==':
                    test.isAlive = False
                    isworking = False
                    lcd.clear()
                    lcd.message('Exit system!')
                test.ready_input = False
                test.barcode = ''
                state = 1   # 接收到有效数据，转入显示状态

        elif state == 1:  # 收到输入数据，显示    
            hostname = run_cmd(cmd)
            
            _current_date_time = datetime.datetime.now()
            d = _current_date_time.strftime('%Y-%m-%d %H:%M:%S')
            
            is_validsn = False
            if len(barcode) == 14:
                is_validsn = True
                sn = barcode
                smtsn = 'None'
            elif len(barcode) == 17:
                is_validsn = True
                sn = 'None'
                smtsn = barcode
            else:
                is_validsn = False  

            if is_validsn == True:
                kwds = (hostname[:-1], sn, d)
                lastid = test.insert_new_aging_record(kwds)
                
                params = (lastid, sn, smtsn)
                test.insert_new_meter_sn_relation(params)
    
                lcd.clear()
                lcd.message('%s\n' % ( barcode[-16:] ) )
                lcd.message('Scan OK!')
                state = 2
            else:
                lcd.clear()
                lcd.message('%s\n' % ( barcode[-16:] ) )
                lcd.message('-----   Error!!!')
                state = 2

        elif state == 2:  # 等待显示结束
            _count -= 1
            if _count <= 0:
                _count = 200
                state = 0

        elif state == 3:  # 其他
            state = 0

        else:             # 其他
            state = 0

        time.sleep(0.01)
        
    print '退出软件'
    test.closedb()
