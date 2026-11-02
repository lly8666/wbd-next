# PLAN027A H973｜补全H972一次性原生派发器自身路径

H972只新增的workflow文件是`m0-plan027a-h972-mss-one-shot.yml`，但on.push.paths写`...-mss-once.yml`，GitHub没有触发本应等待H971整源构建的one-shot。H973仅修该literal，不动任何产品/测试条件；原H971构建[41482859398](https://github.com/lly8666/wbd-next/actions/runs/41482859398)不重启；此新派发器仍要求H971整源PASS和SHA产物后才能真正发Normal及七个窄测试。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct one-shot workflow literal self push path; source/product and qualification gates unchanged."}
```
