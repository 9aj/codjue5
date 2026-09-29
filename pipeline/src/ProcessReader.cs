// Project Jump: read-only COD4 process access. No write/injection/network APIs.
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
namespace PhilLibX.IO {
    public sealed class ProcessReader : IDisposable {
        private IntPtr handle;
        [DllImport("kernel32.dll", SetLastError=true)] static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
        [DllImport("kernel32.dll", SetLastError=true)] static extern bool ReadProcessMemory(IntPtr process, IntPtr address, byte[] buffer, UIntPtr size, out UIntPtr read);
        [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool QueryFullProcessImageName(IntPtr process, uint flags, StringBuilder path, ref uint size);
        public static string ExecutablePath(int pid) {
            IntPtr query = OpenProcess(0x1000, false, pid);
            if(query == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error(), "Cannot query target executable");
            try {
                var path = new StringBuilder(32768); uint size = (uint)path.Capacity;
                if(!QueryFullProcessImageName(query,0,path,ref size)) throw new Win32Exception(Marshal.GetLastWin32Error());
                return path.ToString();
            } finally { CloseHandle(query); }
        }
        public ProcessReader(Process process) {
            handle = OpenProcess(0x10, false, process.Id);
            if (handle == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error(), "Windows denied read-only memory access to COD4. Run the exporter with the same Windows user/elevation as the game.");
        }
        public byte[] ReadBytes(long address, int count) {
            // COD4 is 32-bit; signed pointers must be zero-extended.
            if (address < 0 && address >= int.MinValue) address = unchecked((uint)(int)address);
            if (address < 0x10000 || address > uint.MaxValue || count < 0 || count > 128*1024*1024 || address + count > 0x100000000L)
                throw new InvalidDataException("Invalid COD4 memory range: address=0x" + address.ToString("X") + ", bytes=" + count);
            byte[] data = new byte[count];
            if (count == 0) return data;
            UIntPtr read;
            if (!ReadProcessMemory(handle, new IntPtr(address), data, new UIntPtr((uint)count), out read) || read.ToUInt64() != (ulong)count)
                throw new IOException("Cannot read COD4 memory at 0x" + address.ToString("X") + "; unsupported build, unloaded map or changing process.");
            return data;
        }
        public int ReadInt32(long address) { return BitConverter.ToInt32(ReadBytes(address,4),0); }
        public T ReadStruct<T>(long address) { return PhilLibX.ByteUtil.BytesToStruct<T>(ReadBytes(address,Marshal.SizeOf(typeof(T)))); }
        public string ReadNullTerminatedString(long address, int limit=4096) {
            if (limit < 1 || limit > 4*1024*1024) throw new ArgumentOutOfRangeException("limit");
            using(var result = new MemoryStream()) {
                // Page-bounded reads avoid crossing into an unreadable page after the terminator.
                long cursor = address < 0 ? unchecked((uint)(int)address) : address;
                while(result.Length < limit) {
                    int count = Math.Min(256,Math.Min(limit-(int)result.Length,4096-(int)(cursor%4096)));
                    byte[] bytes = ReadBytes(cursor,count);
                    int end = Array.IndexOf(bytes,(byte)0);
                    result.Write(bytes,0,end < 0 ? bytes.Length : end);
                    if(end >= 0) return Encoding.ASCII.GetString(result.ToArray());
                    cursor += count;
                }
                throw new InvalidDataException("Unterminated COD4 string");
            }
        }
        public void Dispose() { if(handle != IntPtr.Zero) { CloseHandle(handle); handle=IntPtr.Zero; } }
    }
}
