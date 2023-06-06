import p2019B4A70627P_D2_vk as vk

from ctypes import *
from ctypes.wintypes import *
import asyncio, weakref

k32 = windll.kernel32
u32 = windll.user32

LRESULT = c_size_t
HCURSOR = HICON
WNDPROC = WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)

CS_HREDRAW = 0x0002
CS_VREDRAW = 0x0001
CS_OWNDC = 0x0020

IDC_ARROW = LPCWSTR(32512)

WM_CREATE = 0x0001
WM_CLOSE = 0x0010
WM_QUIT = 0x0012
WM_MOUSEWHEEL = 0x020A
WM_RBUTTONDOWN = 0x0204
WM_LBUTTONDOWN = 0x0201
WM_MOUSEMOVE = 0x0200
WM_SIZE = 0x0005
WM_EXITSIZEMOVE = 0x0232

MK_RBUTTON = 0x0002
MK_LBUTTON = 0x0001

WS_CLIPCHILDREN = 0x02000000
WS_CLIPSIBLINGS = 0x04000000
WS_OVERLAPPED = 0x00000000
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_OVERLAPPEDWINDOW = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX

SIZE_MAXIMIZED = 2
SIZE_RESTORED = 0

CW_USEDEFAULT = 0x80000000

SW_SHOWNORMAL = 5

PM_REMOVE = 0x0001

NULL = c_void_p(0)
NULL_WSTR = LPCWSTR(0)

class WNDCLASSEXW(Structure):
    _fields_ = (('cbSize', UINT), ('style', UINT), ('lpfnWndProc', WNDPROC), ('cbClsExtra', c_int),
                ('cbWndExtra', c_int), ('hinstance', HINSTANCE), ('hIcon', HICON), ('hCursor', HCURSOR), 
                ('hbrBackground', HBRUSH), ('lpszMenuName', LPCWSTR), ('lpszClassName', LPCWSTR), ('hIconSm', HICON))

def result_not_null(msg):
    def inner(value):
        if value == 0:
            raise WindowsError(msg + '\n' + FormatError())
        return value
    return inner

GetModuleHandleW = k32.GetModuleHandleW
GetModuleHandleW.restype = result_not_null('Failed to get window module')
GetModuleHandleW.argtypes = (LPCSTR,)

LoadCursorW = u32.LoadCursorW
LoadCursorW.restype = result_not_null('Failed to load cursor')
LoadCursorW.argtypes = (HINSTANCE, LPCWSTR)

RegisterClassExW = u32.RegisterClassExW
RegisterClassExW.restype = result_not_null('Failed to register class')
RegisterClassExW.argtypes = (POINTER(WNDCLASSEXW),)

DefWindowProcW = u32.DefWindowProcW
DefWindowProcW.restype = LPARAM
DefWindowProcW.argtypes = (HWND, UINT, WPARAM, LPARAM)

CreateWindowExW = u32.CreateWindowExW
CreateWindowExW.restype = result_not_null('Failed to create window')
CreateWindowExW.argtypes = (DWORD, LPCWSTR, LPCWSTR, DWORD, c_int, c_int, c_int, c_int, HWND, HMENU, HINSTANCE, c_void_p)

UnregisterClassW = u32.UnregisterClassW
UnregisterClassW.restype = result_not_null('Failed to unregister class')
UnregisterClassW.argtypes = (LPCWSTR, HINSTANCE)

DestroyWindow = u32.DestroyWindow
DestroyWindow.restype = HWND
DestroyWindow.argtypes = (HWND,)

ShowWindow = u32.ShowWindow
ShowWindow.restype = BOOL
ShowWindow.argtypes = (HWND, c_int)

PeekMessageW = u32.PeekMessageW
PeekMessageW.restype = BOOL
PeekMessageW.argtypes = (POINTER(MSG), HWND, UINT, UINT, UINT)

DispatchMessageW = u32.DispatchMessageW
DispatchMessageW.restype = LRESULT
DispatchMessageW.argtypes = (POINTER(MSG),)

TranslateMessage = u32.TranslateMessage
TranslateMessage.restype = BOOL
TranslateMessage.argtypes = (POINTER(MSG),)

PostQuitMessage = u32.PostQuitMessage
PostQuitMessage.restype = None
PostQuitMessage.argtypes = (c_int,)

GetClientRect = u32.GetClientRect
GetClientRect.restype = result_not_null('Failed to get window dimensions')
GetClientRect.argtypes = (HWND, POINTER(RECT))

SetWindowTextW = u32.SetWindowTextW
SetWindowTextW.restype = result_not_null('Failed to set the window name')
SetWindowTextW.argtypes = (HWND, LPCWSTR)


mouse_pos = (0, 0)
resize_target = (0, 0)

def wndproc(window, hwnd, msg, w, l):
    global mouse_pos, resize_target

    if msg == WM_MOUSEMOVE:
        app = window.app()
        x, y = float(c_short(l).value), float(c_short(l>>16).value)
        if w & MK_RBUTTON:
            app.zoom += (mouse_pos[1] - float(y)) * 0.005
        elif w & MK_LBUTTON:
            app.rotation[0] += (mouse_pos[1] - float(y)) * 1.25
            app.rotation[1] += (mouse_pos[0] - float(x)) * 1.25

        mouse_pos = (x,y)
        app.update_uniform_buffers()

    elif msg in (WM_RBUTTONDOWN, WM_LBUTTONDOWN):
        x, y = float(c_short(l).value), float(c_short(l>>16).value)
        mouse_pos = (x,y)

    elif msg == WM_MOUSEWHEEL:
        app = window.app()
        wheel_delta = float(c_short(w>>16).value)
        app.zoom += wheel_delta*0.002
        app.update_uniform_buffers()

    if msg == WM_SIZE:
        resize_target = c_short(l).value, c_short(l>>16).value
        if w in (SIZE_MAXIMIZED, SIZE_RESTORED):
            window.app().resize_display(*resize_target)

    elif msg == WM_EXITSIZEMOVE:
        window.app().resize_display(*resize_target)

    if msg == WM_CREATE:
        pass

    elif msg == WM_CLOSE:
        DestroyWindow(hwnd)
        window.__hwnd = None
        window.app().running = False 
        PostQuitMessage(0)

    else:
        return DefWindowProcW(hwnd, msg, w, l)

    return 0

async def process_events(app):
    listen_events = True
    while listen_events:
        msg = MSG()
        while PeekMessageW(byref(msg), NULL, 0, 0, PM_REMOVE) != 0:
            listen_events = msg.message != WM_QUIT
            TranslateMessage(byref(msg))
            DispatchMessageW(byref(msg))

        await asyncio.sleep(1/30)
    app = app()
    if app is not None:
        await app.rendering_done.wait()

    asyncio.get_event_loop().stop()

class Win32Window(object):
    
    def __init__(self, app):
        self.__wndproc = WNDPROC(lambda hwnd, msg, w, l: wndproc(self, hwnd, msg, w, l))
        self.__class_name = "VULKAN_TEST_"+str(id(self))
        self.__hwnd = None
        self.app = weakref.ref(app)

        mod = GetModuleHandleW(None)

        # Register the window class
        class_def = WNDCLASSEXW(
            cbSize = sizeof(WNDCLASSEXW),
            lpfnWndProc = self.__wndproc,
            style = CS_HREDRAW | CS_VREDRAW | CS_OWNDC,
            cbClsExtra = 0, cbWndExtra = 0,
            hInstance = mod, hIcon = NULL,
            hCursor = LoadCursorW(NULL, IDC_ARROW),
            hbrBackground = NULL,
            lpszMenuName = NULL_WSTR,
            lpszClassName = self.__class_name,
            hIconSm = NULL
        )

        RegisterClassExW(byref(class_def))

        self.__hwnd = CreateWindowExW(
            0, self.__class_name,
            "Python vulkan test",
            WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN | WS_CLIPSIBLINGS,
            CW_USEDEFAULT, CW_USEDEFAULT,
            1280, 720,
            NULL, NULL, mod, NULL
        )

        asyncio.ensure_future(process_events(self.app))

    def __del__(self):
        
        if self.__hwnd != None:
            DestroyWindow(self.__hwnd)

        UnregisterClassW(self.__class_name, GetModuleHandleW(None))

    @property
    def handle(self):
        return self.__hwnd

    def dimensions(self):
        dim = RECT()
        GetClientRect(self.__hwnd, byref(dim))
        return (dim.right, dim.bottom)

    def show(self):
        ShowWindow(self.__hwnd, SW_SHOWNORMAL)

    def set_title(self, title):
        title = c_wchar_p(title)
        SetWindowTextW(self.__hwnd, title)


class WinSwapchain(object):

    def create_surface(self):
        
        app = self.app()
        surface = vk.SurfaceKHR(0)
        surface_info = vk.Win32SurfaceCreateInfoKHR(
            s_type = vk.STRUCTURE_TYPE_WIN32_SURFACE_CREATE_INFO_KHR,
            next= None, flags=0, hinstance=GetModuleHandleW(None),
            hwnd=app.window.handle
        )

        result = app.CreateWin32SurfaceKHR(app.instance, byref(surface_info), None, byref(surface))
        if result == vk.SUCCESS:
            self.surface = surface
        else:
            raise RuntimeError("Failed to create surface")

    def __init__(self, app):
        self.app = weakref.ref(app)
        self.surface = None
        self.swapchain = None
        self.images = None
        self.views = None
        self.create_surface()
        
