// Windows portable driver setup; common GUI and installer entry.
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;

namespace Wbd.Gui {
    public static class DriverSetup {
        public const string XdpVersion = "1.4.0";
        // SHA256 of official signed Wintun 0.14.1 bin/amd64/wintun.dll,
        // independently checked from source-locked H2204 release artifacts.
        public const string WintunAmd64Sha256 =
            "e5da8447dc2c320edc0fc52fa01885c103de8c118481f683643cacc3220dafce";

        public static void RequireIdleAdmin(bool administrator, bool active, bool otherClientBusy) {
            if (!administrator) throw new InvalidOperationException("驱动安装必须使用管理员权限启动 WBD。");
            if (active || otherClientBusy)
                throw new InvalidOperationException("请先断开所有 WBD 客户端并完成原生网络清理后再安装驱动。");
        }

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        delegate int XdpStatus();
        public static int WinXdpStatus(string root) {
            IntPtr lib=LoadLibraryEx(Path.Combine(root,"wbd_engine.dll"),IntPtr.Zero,0x1100);
            if(lib==IntPtr.Zero)return unchecked((int)0x8007007e);
            try {
                IntPtr proc=GetProcAddress(lib,"wbd_m0_win_xdp_driver_status");
                if(proc==IntPtr.Zero)return unchecked((int)0x8007007f);
                return ((XdpStatus)Marshal.GetDelegateForFunctionPointer(proc,typeof(XdpStatus)))();
            }finally{FreeLibrary(lib);}
        }
        static void RunSetup(string file,string args,string root) {
            using(var p=Process.Start(new ProcessStartInfo(file,args) {
                UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=root,
                RedirectStandardOutput=true,RedirectStandardError=true
            })){
                var output=p.StandardOutput.ReadToEndAsync();
                var error=p.StandardError.ReadToEndAsync();
                p.WaitForExit();
                if(p.ExitCode!=0)throw new InvalidOperationException(file+" exit="+p.ExitCode+" "+output.Result+" "+error.Result);
            }
        }
        public static string InstallWinXdp(string root) {
            if(WinXdpStatus(root)==0)return "WinXDP 已就绪（原生 socket / XSKMAP API）。";
            string dir=Path.Combine(root,"drivers","winxdp");
            string inf=Path.Combine(dir,"xdp.inf"), manifest=Path.Combine(dir,"xdppcw.man");
            if(!File.Exists(inf)||!File.Exists(manifest))throw new FileNotFoundException("随包 WinXDP 1.4 驱动文件缺失，请完整解压发行包。");
            // Exact official setup operations; no eBPF, PA or policy change.
            RunSetup("netcfg.exe","-v -l \""+inf+"\" -c s -i ms_xdp",dir);
            RunSetup("lodctr.exe","/m:\""+manifest+"\" \""+Path.Combine(Environment.SystemDirectory,"drivers")+"\"",dir);
            int status=WinXdpStatus(root);
            if(status!=0)throw new InvalidOperationException("WinXDP 安装后 API 尚不可用：0x"+unchecked((uint)status).ToString("X8")+"。请检查系统已有驱动版本或重启后重新检测。");
            return "WinXDP "+XdpVersion+" 已安装，原生 socket / XSKMAP API 检测通过。";
        }
        public static string InstallAll(string root){
            var d=Dependencies.Detect(new PortableStore(root));
            RequireIdleAdmin(d.Admin,false,d.ClientBusy);
            return InstallWinXdp(root)+"\n"+InstallWintunWithTemporaryAdapter(Path.Combine(root,"wintun.dll"));
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        static extern IntPtr LoadLibraryEx(string name, IntPtr file, uint flags);
        [DllImport("kernel32.dll", SetLastError = true)]
        static extern bool FreeLibrary(IntPtr module);
        [DllImport("kernel32.dll", CharSet = CharSet.Ansi, ExactSpelling = true)]
        static extern IntPtr GetProcAddress(IntPtr module, string procedure);
        [UnmanagedFunctionPointer(CallingConvention.StdCall, CharSet = CharSet.Unicode)]
        delegate IntPtr CreateAdapter(
            [MarshalAs(UnmanagedType.LPWStr)] string name,
            [MarshalAs(UnmanagedType.LPWStr)] string tunnelType,
            IntPtr requestedGuid);
        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        delegate void CloseAdapter(IntPtr adapter);

        public static void VerifyPinnedWintunDll(string dllPath) {
            string full = Path.GetFullPath(dllPath);
            var file = new FileInfo(full);
            if (!file.Exists || file.Length < 1024 || file.Length > 5L * 1024L * 1024L ||
                (file.Attributes & FileAttributes.ReparsePoint) != 0)
                throw new InvalidDataException("随包 Wintun 官方 DLL 不存在或异常。");
            using (var stream = File.OpenRead(full))
            using (var digest = SHA256.Create()) {
                string actual = BitConverter.ToString(digest.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
                if (!string.Equals(actual, WintunAmd64Sha256, StringComparison.Ordinal))
                    throw new InvalidDataException("随包 Wintun DLL 与官方签名版本的固定 SHA256 不一致，禁止加载。");
            }
        }

        public static string InstallWintunWithTemporaryAdapter(string dllPath) {
            VerifyPinnedWintunDll(dllPath);
            // The temporary setup adapter has a unique name and is NOT the
            // real product adapter. Never use a configured WBD alias or touch
            // another owner's Wintun handles. Create registers the driver;
            // Close removes only this newly created temporary adapter.
            IntPtr lib = LoadLibraryEx(Path.GetFullPath(dllPath), IntPtr.Zero, 0x1100);
            if (lib == IntPtr.Zero)
                throw new InvalidOperationException("无法加载官方 Wintun DLL，系统错误：" +
                                                    Marshal.GetLastWin32Error());
            try {
                IntPtr createPtr = GetProcAddress(lib, "WintunCreateAdapter");
                IntPtr closePtr = GetProcAddress(lib, "WintunCloseAdapter");
                if (createPtr == IntPtr.Zero || closePtr == IntPtr.Zero)
                    throw new InvalidDataException("官方 Wintun API 不完整，驱动未安装。");
                var create = (CreateAdapter)Marshal.GetDelegateForFunctionPointer(createPtr, typeof(CreateAdapter));
                var close = (CloseAdapter)Marshal.GetDelegateForFunctionPointer(closePtr, typeof(CloseAdapter));
                string name = "WBD-Setup-" + Guid.NewGuid().ToString("N").Substring(0, 12);
                IntPtr adapter = create(name, "WBD", IntPtr.Zero);
                if (adapter == IntPtr.Zero)
                    throw new InvalidOperationException("Wintun 临时网卡创建失败，系统错误：" +
                                                        Marshal.GetLastWin32Error());
                try {
                    // Successfully opening an owned adapter proves PnP setup
                    // was attempted, not that a production tunnel is ready.
                } finally {
                    close(adapter);
                }
                return "Wintun 官方驱动已完成一次真实临时网卡创建并撤销；正式 WBD 网卡仅在连接时建立。";
            } finally {
                FreeLibrary(lib);
            }
        }
    }
}
