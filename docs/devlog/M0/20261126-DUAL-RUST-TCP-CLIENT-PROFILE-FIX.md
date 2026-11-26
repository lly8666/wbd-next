# Client CPU profile fixture correction

Run 45813155885 job 139885951224 failed before launching product: installed Ubuntu linux-tools-generic, `find /usr/lib/linux-tools -name perf -type f` did not select its symlinked executable, `test -x` exited 1, no product/measurement/artifact. Preserve FAIL fixture; corrected path follows symlinks and checks version, same previously measured B binary and fixture. Supersedes profile attempt only; compiler ABBA 45813155937 unchanged.

Corrected harness SOURCE 6674e6ff26c2fe1ed255e7868f7728267bd5a7fa run 45813361467 in progress; no duplicate launch. Compiler run 45813155937 still in progress on bbbe025.
