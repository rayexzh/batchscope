"""Capture only this application's own windows for the short demonstration."""
from pathlib import Path
import sys,time,tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import ctypes
from ctypes import wintypes
import struct,zlib,binascii
def capture(window, path):
    user, gdi = ctypes.windll.user32, ctypes.windll.gdi32
    user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user.GetAncestor.restype = wintypes.HWND
    user.GetDC.argtypes = [wintypes.HWND]
    user.GetDC.restype = wintypes.HDC
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    gdi.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi.CreateCompatibleDC.restype = wintypes.HDC
    gdi.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    gdi.SelectObject.restype = wintypes.HANDLE
    gdi.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi.DeleteDC.argtypes = [wintypes.HDC]
    gdi.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    window.update()
    hwnd = user.GetAncestor(window.winfo_id(), 2)
    rect = wintypes.RECT()
    user.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right-rect.left, rect.bottom-rect.top
    dc = user.GetDC(hwnd)
    memory = gdi.CreateCompatibleDC(dc)
    bitmap = gdi.CreateCompatibleBitmap(dc, width, height)
    old = gdi.SelectObject(memory, bitmap)
    try:
        assert user.PrintWindow(hwnd, memory, 2), 'PrintWindow failed'
        gdi.SelectObject(memory, old)
        info = ctypes.create_string_buffer(struct.pack('<IiiHHIIiiII',40,width,-height,1,32,0,width*height*4,0,0,0,0))
        pixels = ctypes.create_string_buffer(width*height*4)
        assert gdi.GetDIBits(memory, bitmap, 0, height, pixels, info, 0) == height
        raw = pixels.raw
        rgba = bytearray(len(raw))
        rgba[0::4], rgba[1::4], rgba[2::4] = raw[2::4], raw[1::4], raw[0::4]
        rgba[3::4] = b'\xff' * (width*height)
        rows = b''.join(b'\x00'+rgba[i*width*4:(i+1)*width*4] for i in range(height))
        def chunk(kind,data):
            return struct.pack('>I',len(data))+kind+data+struct.pack('>I',binascii.crc32(kind+data)&0xffffffff)
        path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))
                         +chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b''))
    finally:
        gdi.SelectObject(memory, old)
        gdi.DeleteObject(bitmap)
        gdi.DeleteDC(memory)
        user.ReleaseDC(hwnd, dc)

import tkinter as tk
from app import Window
from quality_ops import generate,analyse
from audit_trail import generate_audit
from ui_theme import enable_dpi_awareness

def main():
    enable_dpi_awareness()
    folder=ROOT/'outputs/short-demo-060'
    folder.mkdir(parents=True,exist_ok=True)
    inputs=folder/'inputs'
    if not inputs.exists():generate(inputs)
    result=analyse(inputs,Path(tempfile.mkdtemp(prefix='captured-',dir=folder))/'quality','2026-06-30')
    root=tk.Tk();owner=Window(root)
    try:
        owner.language='en';owner.result=result;owner.inputs.set(str(inputs));owner.apply_view()
        owner.theme='dark';owner.apply_view()
        root.geometry('1150x800');root.update()
        audit=owner.open_audit();audit.window.geometry('1150x760')
        log=folder/'audit_events.csv'
        if not log.exists():generate_audit(log,[result['operations']['batches'][0]['batch_id']])
        audit.load(log)
        for _ in range(5):root.update();time.sleep(.04)
        screenshots=ROOT/'docs/screenshots'
        screenshots.mkdir(parents=True,exist_ok=True)
        capture(audit.window,screenshots/'audit-review-en.png')
        audit.window.withdraw()
        view=owner.open_timeline();view.window.geometry('1150x820')
        view.dates.set('2026-04-30,2026-05-31,2026-06-30,2026-07-31');view.start()
        deadline=time.monotonic()+30
        while view.busy and time.monotonic()<deadline:root.update();time.sleep(.03)
        assert view.result
        for _ in range(5):root.update();time.sleep(.04)
        capture(view.window,screenshots/'multi-date-en.png')
        (folder/'quality-timeline.json').write_text(__import__('json').dumps(view.result,indent=2),encoding='utf-8')
        print('Captured audit review and four-date quality timeline.')
    finally:root.destroy()

if __name__=='__main__':main()
