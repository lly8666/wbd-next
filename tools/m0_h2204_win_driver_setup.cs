// H2204 V4v2 WinForms driver setup: explicit user action only.
// Npcap Free installer never ships with WBD: the user fetches it
// directly from https://npcap.com and selects the signed local file.
// Wintun is distributed only as the pinned official signed 0.14.1 DLL.
// No silent Npcap flags, downloading third-party binaries to our servers,
// driver bypass, route/DNS modification, or foreign-adapter removal.
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.RegularExpressions;

namespace Wbd.Gui {
    public static class DriverSetup {
        public const string NpcapDownloadURL = "https://npcap.com/#download";
        // SHA256 of official signed Wintun 0.14.1 bin/amd64/wintun.dll,
        // independently checked from source-locked H2204 release artifacts.
        public const string WintunAmd64Sha256 =
            "e5da8447dc2c320edc0fc52fa01885c103de8c118481f683643cacc3220dafce";

        public static void RequireIdleAdmin(bool administrator, bool active, bool otherClientBusy) {
            if (!administrator) throw new InvalidOperationException("驱动安装必须使用管理员权限启动 WBD。");
            if (active || otherClientBusy)
                throw new InvalidOperationException("请先断开所有 WBD 客户端并完成原生网络清理后再安装驱动。");
        }

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        struct WinTrustFileInfo {
            public uint cbStruct;
            public IntPtr pcwszFilePath;
            public IntPtr hFile;
            public IntPtr pgKnownSubject;
        }
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        struct WinTrustData {
            public uint cbStruct;
            public IntPtr pPolicyCallbackData;
            public IntPtr pSIPClientData;
            public uint dwUIChoice;
            public uint fdwRevocationChecks;
            public uint dwUnionChoice;
            public IntPtr pFile;
            public uint dwStateAction;
            public IntPtr hWVTStateData;
            public IntPtr pwszURLReference;
            public uint dwProvFlags;
            public uint dwUIContext;
        }
        [DllImport("wintrust.dll", CharSet = CharSet.Unicode, ExactSpelling = true)]
        static extern int WinVerifyTrust(IntPtr hwnd, ref Guid action, ref WinTrustData data);
        static readonly Guid GenericVerifyV2 = new Guid("00AAC56B-CD44-11d0-8CC2-00C04FC295EE");

        // Check actual Windows Authenticode signature trust, not merely an
        // embedded certificate or a filename that an attacker can rename.
        static void RequireTrustedSignature(string path) {
            IntPtr pathMemory = IntPtr.Zero, fileMemory = IntPtr.Zero;
            try {
                pathMemory = Marshal.StringToHGlobalUni(path);
                var file = new WinTrustFileInfo {
                    cbStruct = (uint)Marshal.SizeOf(typeof(WinTrustFileInfo)),
                    pcwszFilePath = pathMemory, hFile = IntPtr.Zero, pgKnownSubject = IntPtr.Zero
                };
                fileMemory = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(WinTrustFileInfo)));
                Marshal.StructureToPtr(file, fileMemory, false);
                var data = new WinTrustData {
                    cbStruct = (uint)Marshal.SizeOf(typeof(WinTrustData)),
                    dwUIChoice = 2, // WTD_UI_NONE
                    dwRevocationChecks = 0,
                    dwUnionChoice = 1, // WTD_CHOICE_FILE
                    pFile = fileMemory, dwStateAction = 0,
                    dwProvFlags = 0, dwUIContext = 0
                };
                var action = GenericVerifyV2;
                int result = WinVerifyTrust(IntPtr.Zero, ref action, ref data);
                if (result != 0)
                    throw new InvalidDataException("安装程序数字签名未通过 Windows 信任验证：" +
                                                   "0x" + unchecked((uint)result).ToString("X8"));
            } finally {
                if (fileMemory != IntPtr.Zero) Marshal.FreeHGlobal(fileMemory);
                if (pathMemory != IntPtr.Zero) Marshal.FreeHGlobal(pathMemory);
            }
        }

        public static void VerifyOfficialNpcapInstaller(string selectedPath) {
            if (string.IsNullOrWhiteSpace(selectedPath))
                throw new InvalidDataException("请选择官网下载的 Npcap 安装程序。");
            string full = Path.GetFullPath(selectedPath);
            string name = Path.GetFileName(full);
            if (!Regex.IsMatch(name, @"^npcap-[0-9][A-Za-z0-9._-]*\.exe$",
                               RegexOptions.IgnoreCase | RegexOptions.CultureInvariant))
                throw new InvalidDataException("仅接受 Npcap 官方版本命名的安装程序 npcap-版本.exe。");
            var info = new FileInfo(full);
            if (!info.Exists || info.Length < 1024 || info.Length > 200L * 1024L * 1024L ||
                (info.Attributes & FileAttributes.ReparsePoint) != 0)
                throw new InvalidDataException("Npcap 安装文件缺失、大小异常或为重解析链接。");
            RequireTrustedSignature(full);
            using (var certificate = new X509Certificate2(X509Certificate.CreateFromSignedFile(full))) {
                string subject = certificate.Subject;
                if (subject.IndexOf("Nmap Software", StringComparison.OrdinalIgnoreCase) < 0 &&
                    subject.IndexOf("Insecure.Com", StringComparison.OrdinalIgnoreCase) < 0)
                    throw new InvalidDataException("Npcap 安装程序签名者不是官方 Nmap Software；拒绝运行。");
            }
        }

        public static string RunInteractiveNpcapInstaller(string selectedPath) {
            VerifyOfficialNpcapInstaller(selectedPath);
            // No /S, no unattended installation, no automatic acceptance
            // of license. The original signed GUI wizard is mandatory.
            var psi = new ProcessStartInfo(Path.GetFullPath(selectedPath)) {
                UseShellExecute = true, Verb = "runas",
                WorkingDirectory = Path.GetDirectoryName(Path.GetFullPath(selectedPath))
            };
            using (var p = Process.Start(psi)) {
                if (p == null) throw new InvalidOperationException("Npcap 安装向导未启动。");
                if (!p.WaitForExit(600000))
                    return "Npcap 安装向导仍在运行；完成后点击“重新检测”，不可按通过处理。";
                if (p.ExitCode == 3010)
                    return "Npcap 安装程序要求重新启动 Windows。重启前不能认定驱动已就绪。";
                if (p.ExitCode != 0)
                    throw new InvalidOperationException("Npcap 安装向导退出码：" + p.ExitCode +
                                                        "；请检查官方安装日志。");
            }
            return "Npcap 官方安装向导已退出；请看下方真实驱动检测结果。";
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
