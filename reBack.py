#coding=utf-8
import os
import time
import hashlib
import sqlite3
import shutil
import sys
import json
import threading
import subprocess
#gui
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QMessageBox
import win

sdirs  = [] #default dirs
backStatus = 0
# 快速操作QtextBrowser会导致应用崩溃（如在for里调用logs）
class backui():
    def init(db=True):
        pButton = QtWidgets.QPushButton()
        pButton.clicked.connect(backui.selectPath)
        pButton.setMaximumSize(QtCore.QSize(140, 29))
        pButton.setMinimumSize(QtCore.QSize(140, 29))
        pButton.setObjectName("pathButton")
        pButton.setText("选择备份目录")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/del/image/addfile.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        pButton.setIcon(icon)
        rWindow.tableWidget.setCellWidget(0, 2, pButton)
        rWindow.tableWidget.setSpan(0, 0, 1, 2)  #改变行数/列数,合并的行数/列数
        #width:800(500+150+150)
        rWindow.tableWidget.setColumnWidth(0, 500)
        rWindow.tableWidget.setColumnWidth(1, 143)
        rWindow.tableWidget.itemClicked.connect(backui.delItem)
        #no edit
        item = QtWidgets.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsDragEnabled)
        rWindow.tableWidget.setItem(0, 0, item)
        #<init
        dbfile = os.path.join(os.getcwd(), 'reBack.sqlite')
        res = dbs.dir_get(dbfile)
        if res:
            backui.logs('*** 已载入上次备份方案')
            dates = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(res[3]))
            backui.logs('*** 上次备份时间: %s'%dates)
            global backStatus
            if res[4]>0:
                backStatus = 1
                backui.logs('*** 上次备份状态: 完成')
            else:
                backui.logs('*** 上次备份状态: 失败')
                rWindow.reBack.checkState()
            dbdirs = json.loads(res[1])
            rWindow.backPath.setText(res[2])
            for dir in dbdirs:
                backui.addItem(dir)
        else:
            backui.logs('*** 选择备份文件目录 和 备份位置后点击:开始备份！')
        #init backPath
        rWindow.backPath.clicked.connect(backui.backPath)
        #init backButton
        rWindow.pushButton.clicked.connect(backui.start)
    def start(self):
        rWindow.pushButton.setEnabled(False)
        thread = myBackup()
        thread.daemon = True
        thread.start()
    def addItem(path):
        row = rWindow.tableWidget.rowCount() - 1
        if backui.addPath(path):
            rWindow.tableWidget.insertRow(row)
            rWindow.tableWidget.scrollToBottom()
        else:
            return False
        item = QtWidgets.QTableWidgetItem()
        item.setText(path)
        rWindow.tableWidget.setItem(row, 0, item)
        item = QtWidgets.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsDragEnabled)
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        item.setText('-/-')
        rWindow.tableWidget.setItem(row, 1, item)

        #item = QtWidgets.QTableWidgetItem()
        #icon = QtGui.QIcon()
        #icon.addPixmap(QtGui.QPixmap(":/del/image/x64x2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        ##item.setText('删除')
        #item.setIcon(icon)
        #item.setTextAlignment(QtCore.Qt.AlignCenter)
        #rWindow.tableWidget.setItem(row, 2, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Segoe Script")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        item.setFont(font)
        item.setText("X")
        brush = QtGui.QBrush(QtGui.QColor(194, 17, 17))
        brush.setStyle(QtCore.Qt.NoBrush)
        item.setForeground(brush)
        rWindow.tableWidget.setItem(row, 2, item)
    def delItem(item):
        if item:
            row = item.row()
            col = item.column()
            item = rWindow.tableWidget.item(row,0)
            path = item.text()
            if path and col==2:
                if backui.delPath(path):
                    rWindow.tableWidget.removeRow(row)
                    backui.logs('已取消目录: %s'%(path))
                else:
                    backui.msg('操作失败', '请重试或重启此应用. ')
    def addPath(path):
        for dir in sdirs:
            if dir==path:
                backui.msg('操作失败', '此目录已存在. ')
                return False
        sdirs.append(path)
        return True
    def delPath(path):
        for dir in sdirs:
            if dir==path:
                sdirs.remove(path)
                return True
        return False
    def msg(tit, msg):
        msg_box = QMessageBox(QMessageBox.Warning, tit, msg)
        msg_box.show()
        msg_box.exec_()
    def logs(txt, end=0):
        if end==1:
            #tb = rWindow.textBrowser.toPlainText()
            #rWindow.textBrowser.setPlainText(tb)
            rWindow.textBrowser.insertPlainText(txt)
        else:
            rWindow.textBrowser.append(txt)
    def logs_reset(txt):
        tb = rWindow.textBrowser.toPlainText()
        rWindow.textBrowser.setPlainText(tb)
    def selectPath(self):
        open = QFileDialog()
        #rWindow.path=open.getOpenFileNames()
        rWindow.path = open.getExistingDirectory().replace("/", "\\")
        if rWindow.path:
            backui.logs('已选择目录: %s'%(rWindow.path))
            #rWindow.pushPath.setText(rWindow.path[0][0])
            #rWindow.pushPath.setText(rWindow.path)
            backui.addItem(rWindow.path)
    def backPath(self):
        open = QFileDialog()
        rWindow.path = open.getExistingDirectory().replace("/", "\\")
        if rWindow.path:
            if os.path.dirname(rWindow.path)==rWindow.path:
                backui.msg('Warning', '存储位置必须指定一个目录.')
            else:
                rWindow.backPath.setText(rWindow.path)
                backui.logs('已选择存储目录: %s'%(rWindow.path))

class myBackup(threading.Thread):
    def run(self):
        if not sdirs:
            #backui.msg('Warning', '未选择需要备份的目录')
            backui.logs('<b style="color:#f00;">Warning:</b> 未选择备份文件目录')
            rWindow.pushButton.setEnabled(True)
            return
        backpath = rWindow.backPath.text()
        if not os.path.isdir(backpath):
            #backui.msg('Warning', '未选择备份存储的目录')
            backui.logs('<b style="color:#f00;">Warning:</b> 未选择备份存储目录')
            rWindow.pushButton.setEnabled(True)
            return
        backup = backpath
        #dbfile = os.path.join(backpath, 'reBack.sqlite')
        dbfile = os.path.join(os.getcwd(), 'reBack.sqlite')
        #同盘禁止备份
        for dir in sdirs:
            if not os.path.exists(dir):
                #backui.msg('Warning', '选择的备份目录不存在 ')
                backui.logs('<b style="color:#f00;">Warning:</b> 目录不存在: %s'%dir)
                rWindow.pushButton.setEnabled(True)
                return
            if backpath[0]==dir[0]:
                #backui.msg('Warning', '备份存储目录和备份文件不可同为【%s】盘 '%dir[0])
                backui.logs('<b style="color:#f00;">Warning:</b> 备份目录和备份存储不可同为【%s】盘, 请为备份存储选择其他盘符.'%dir[0])
                rWindow.pushButton.setEnabled(True)
                return
        #db.save path...
        backui.logs('*** 备份初始化')
        dbs.dir_save(dbfile, json.dumps(sdirs), backpath)
        dbs.toBackup(dbfile, sdirs, backpath)

class dbs():
    dbcon = None
    sdirs = []
    backup = ''
    redirs = {}
    delfiles = {}
    def toBackup(dbfile, sdirs, backup):
        global backStatus
        dbs.sdirs = sdirs
        dbs.backup = backup
        dbs.rm_dira(dbfile)
        backui.logs('*** 扫描所有备份文件...')
        fnum = dbs.ex_sdirs()
        backui.logs('(%s)'%(fnum), 1)
        #备份状态
        if not rWindow.reBack.isChecked() and backStatus == 1:
            backui.logs('*** 扫描备份存储文件...(skip)')
        else:
            dbs.rm_dirb(dbfile)
            backui.logs('*** 扫描备份存储文件...')
            fnum = dbs.ex_backup()
            backui.logs('(%s)'%(fnum), 1)
        backui.logs('*** 同步中...')
        #update times
        db = dbs.dbcon.cursor()
        db.execute("update dirs set status='0' where id='1'")
        dbs.diff_dir()
        db.execute("update dirs set status='1' where id='1'")
        dbs.dbcon.commit()
        dbs.dbcon.close()
        #update end
        fnum = dbs.ex_backup_fnum()
        backui.logs('<p style="color:#f00;">*** 备份已完成 (%s)</p>'%(fnum))
        #backup sqlite
        dates = time.strftime('%Y%m%d-%H%M%S_')
        logdir = os.path.join(os.path.dirname(backup), '000Logs')
        if not os.path.isdir(logdir):
            os.mkdir(logdir)
        dbfile = os.path.join(os.getcwd(), 'reBack.sqlite')
        bsfile = os.path.join(logdir, dates + 'reBack.sqlite')
        dblog  = os.path.join(os.getcwd(), dates + 'reBack.log')
        bslog  = os.path.join(logdir, dates + 'reBack.log')
        shutil.copy2(dbfile, bsfile)
        #print log
        fstr = ''
        if dbs.redirs:
            for key in dbs.redirs:
                fstr = fstr + '--------------------------------------------------------\n'
                fnum = len(dbs.redirs[key])
                fstr = fstr + '重复文件(%s):'%(fnum)
                for fkey in dbs.redirs[key]:
                    fstr = fstr + '\n' + fkey
        if dbs.delfiles:
            fstr = fstr + '\n\n--------------------------------------------------------\n'
            fstr = fstr + '备份盘未清理文件(%s):'%(len(dbs.delfiles))
            for key in dbs.delfiles:
                #print(type(dbs.delfiles[key]))
                fstr = fstr + '\n' + dbs.delfiles[key]

        #backui.logs('%s'%fstr)
        f = open(dblog, 'a')
        f.write(fstr)
        f.close()
        shutil.copy2(dblog, bslog)
        backui.logs('*** 日志已保存 (%s)'%(dblog))
        subprocess.call('notepad %s' %(dblog))

        #print(rWindow.textBrowser.toHtml())
    def db_init(dbfile):
        dbfile = dbfile.replace('\\', '/')
        #if os.path.isfile(dbfile):
        #    os.remove(dbfile)
        if not dbs.dbcon:
            dbs.dbcon = sqlite3.connect(dbfile)
    def db_close():
        dbs.dbcon.close()
        dbs.dbcon = None
    def dir_save(dbfile, dirs, back):
        times = time.time()
        dbs.db_init(dbfile)
        db = dbs.dbcon.cursor()
        db.execute("create table if not exists dirs (id int(1) primary key, dirs text NOT NULL, back text NOT NULL, times int(10), status boolean NOT NULL default 0)")
        db.execute("replace into dirs values (?,?,?,?,?)", (1, dirs, back, times,0))
        dbs.dbcon.commit()
        dbs.db_close()
    def dir_get(dbfile):
        if os.path.isfile(dbfile):
            dbcon = sqlite3.connect(dbfile)
            db = dbcon.cursor()
            db.execute("select * from dirs where id='1'")
            res = db.fetchall()
            if res:
                return res[0]
        return []
    def rm_dira(dbfile):
        dbs.db_init(dbfile)
        db = dbs.dbcon.cursor()
        db.execute('drop table if exists diraaa')
        db.execute("create table if not exists diraaa (md5 varchar(32) primary key, fname text NOT NULL, times int(10))")
    def rm_dirb(dbfile):
        dbs.db_init(dbfile)
        db = dbs.dbcon.cursor()
        db.execute('drop table if exists dirbbb')
        db.execute("create table if not exists dirbbb (md5 varchar(32) primary key, fname text NOT NULL, times int(10))")
    def diff_dir():
        #获取b表旧记录，删除文件和记录
        db = dbs.dbcon.cursor()
        db.execute("select * from diraaa")
        res_a = db.fetchall()
        db.execute("select * from dirbbb")
        res_b = db.fetchall()
        times = int(time.time())
        #diff data
        fnum = 0
        bDict = {}
        bDictDel = {}
        for i in range(len(res_b)):
            bDict[res_b[i][0]] = res_b[i][1]
        kw=len(res_a)
        for i in range(len(res_a)):
            #kwnew = int( (i+1) * kw - kwold )
            #kwold = int( (i+1) * kw )
            #if kwnew>0:
                #up3 = '#'.center(kwnew,'#')
                #rWindow.textBrowser.insertHtml('<p style="background:#93c47d;width:10px;">%s</p>'%(up3))
                #backui.logs_reset('10%')
            n = int((i+1) * 100 / kw)
            rWindow.pushButton.setText("备份(%s%%)"%(n))

            fnum += 1
            fname = res_a[i][1].replace(':', '', 1)
            newname = os.path.join(dbs.backup, fname) #backup /path/file
            (newpath, tmpname) = os.path.split(newname) #path + file
            if not os.path.isdir(newpath):
                os.makedirs(newpath)

            md5 = res_a[i][0]
            if md5 in bDict:
                # 如果b表存在, 目录不同，则b表move过去，更新times
                if newname.encode('utf-8') != bDict[md5].encode('utf-8'):
                    print('Move: %s ***  %s'%(bDict[md5], newname))
                    shutil.move(bDict[md5], newname)
                    db.execute("replace into dirbbb values (?,?,?)", (md5, newname, times))
                #del bDict
                bDictDel[md5] = bDict[md5]
                del bDict[md5]
            # 如果a表数据重复存在，则跳过
            elif md5 in bDictDel:
                #backui.logs('<p style="color:#f00;">*** 备份文件重复: %s</p>'%(newname))
                continue
            else:
                print('Copy File %s'%(newname))
                # 如果b表没有, 则a表copy过去，更新times
                #if os.path.isfile(newname):
                #    backui.logs('<p style="color:#f00;">*** 备份盘文件重复: %s</p>'%(newname))
                #else:
                shutil.copy2(res_a[i][1], newpath)
                #update db
                md = hashlib.md5()
                md_file = open(newname, 'rb')
                md.update(md_file.read())
                md_file.close()
                md5 = md.hexdigest()
                db.execute("replace into dirbbb values (?,?,?)", (md5, newname, times))
        #close db
        #dbs.dbcon.close()

        #del bDict file
        dbs.delfiles = bDict
        if not rWindow.delBack.isChecked():
            for key in bDict:
                #print('Del: **** %s'%(bDict[key]))
                if os.path.isfile(bDict[key]):
                    os.remove(bDict[key])
    def ex_sdirs():
        fnum = 0
        for dir in dbs.sdirs:
            fnum += dbs.ex_md5(dir, 'diraaa')
        return fnum
    def ex_backup():
        fnum = 0
        if not os.path.isdir(dbs.backup):
            try:
                os.mkdir(dbs.backup)
            except:
                backui.logs('<b style="color:#f00;">Warning:</b> 存储目录异常: %s'%dbs.backup)
                return fnum
        fnum = dbs.ex_md5(dbs.backup, 'dirbbb')
        return fnum
    def ex_backup_fnum():
        fnum = 0
        for(dirname, subdir, subfile) in os.walk(dbs.backup):
            for fname in subfile:
                file2 = os.path.join(dirname, fname)
                if os.path.isfile(file2):
                    fnum += 1
        return fnum
    def ex_md5(dirs, dbname):
        fnum = 0
        db = dbs.dbcon.cursor()
        now = int(time.time())
        dot = ['.', '..', '...']
        nowdot = 0
        for(dirname, subdir, subfile) in os.walk(dirs):
            #print('dirname is %s, subdir is %s, subfile is %s' % (dirname, subdir, subfile))
            for fname in subfile:
                now2 = int(time.time())
                if now2-now > 1:
                    now = now2
                    rWindow.pushButton.setText("扫描中(%s)"%(dot[nowdot]))
                    nowdot = nowdot+1 if nowdot<2 else 0
                file2 = os.path.join(dirname, fname)
                if os.path.isfile(file2):
                    fnum += 1
                    md5 = dbs.md5_file(file2)
                    if dbname=='diraaa':
                        db.execute("select * from diraaa where md5='%s'"%(md5))
                        res = db.fetchall()
                        #重复文件
                        if res:
                            #dbs.redirs.append()
                            if md5 in dbs.redirs.keys():
                                dbs.redirs[md5].append(file2)
                            else:
                                dbs.redirs[md5] = []
                                dbs.redirs[md5].append(res[0][1])
                                dbs.redirs[md5].append(file2)
                            continue
                        else:
                            db.execute("replace into %s values (?,?,?)"%(dbname), (md5, file2, 0))
                    else:
                        db.execute("replace into %s values (?,?,?)"%(dbname), (md5, file2, 0))
                    #print('%s -- %s' % (md5, file2))
                else:
                    #遇到非文件退出
                    backui.logs('<b style="color:#f00;">Warning:</b> 异常文件: %s'%file2)
                    #print('not file')
                    #dbs.dbcon.close()
                    #exit()
        dbs.dbcon.commit()
        return fnum
    def md5_file(fname):
        fsize = os.path.getsize(fname)
        sizeM = round(fsize/1024/1024, 2)
        if sizeM > 50:
            #局部hash
            m = hashlib.md5()
            md_file = open(fname, 'rb')
            m.update(md_file.read(8192))
            md_file.seek(8192, 2)
            m.update(md_file.read(8192))
            md_file.close()
            m.update( str(fsize).encode('utf-8') )
            m.update( str(os.path.getmtime(fname)).encode('utf-8') ) #!!!
            md5 = m.hexdigest()
            return md5
        else:
            #文件hash
            m = hashlib.md5()
            with open(fname, "rb") as fh:
                while True:
                    buf = fh.read(2**20)
                    if not buf:
                        break
                    m.update(buf)
            return m.hexdigest()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    rWindow = win.rebackUI()
    rWindow.show()
    backui.init()
    sys.exit(app.exec_())
