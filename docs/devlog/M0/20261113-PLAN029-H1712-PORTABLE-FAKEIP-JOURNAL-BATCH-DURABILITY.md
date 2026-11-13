# PLAN029 H1712｜真实可恢复FakeIP批量文件提交；补 H1711 feature card 16KiB 门

- H1711 [M0-WIN-LINUX43366345223](https://github.com/lly8666/wbd-next/actions/runs/43366345223) SOURCE `c939d868f6c6fdf8e4aa4eaec28db2899b91167d` Windows324/Linux299 Rust eligible library PASS；3项CN CNAME/多A/共享CDN、不持久化Fake拒发/TTL0及HTTPS/AAAA NODATA DNS wire测试均通过。H1711 [Governance43366345201](https://github.com/lly8666/wbd-next/actions/runs/43366345201) governance PASS，但Feature catalog因dns-split-ipv6.json 16KiB预算FAIL，本批只收短历史scope展示、保留所有条目、status/source_sha/evidence和原完整证据，不删旧失败。
- 新 `v4_client_fake_journal.rs`：portable应用目录绝对路径内**单冷DNS owner**，append-only有CRC32帧，每批最多128条、256KiB，有界16MiB磁盘上限；同一个fake不能在旧隔离期内重绑定不同QNAME/真实A，文件magic/尾部损坏/跨次身份冲突**不自动清空**，拒绝新Fake答案。真正`File::sync_data()`成功后才对该批`FakeAllocator::acknowledge_durable`，写/同步失败poison本代writer，不伪造已Applied。文件只由DNS缺失时的批量持久化写，没有DATA逐包磁盘/线程，未要求每DNS请求单独fsync。
- 新测试直接在Windows/Linux真实临时文件上Open→双条batch sync→TTL renewal append（不重写全表）→Drop→重新Open/restore→真实CN Fake DNS wire生成；另测破坏CRC/外来头拒绝、同批重复fake拒绝与不ack。当前为源码/自动单测待收，真实业务DNS仍未接，不能用该test代替真Wintun/OS DNS入口。
- **长时边界**：当前journal 16MiB硬上限有局部明确失败；还需在产品压力前完成安全批量compaction，不得靠持续扩大文件上限掩盖RSS/磁盘成本。生产Default缓存合并、server bootstrap单DNS、GUI/Normal/Game4及D1-D5/P1-P2仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect H1711 Win/Linux FakeIP DNS wire unit PASS; fix bounded feature card while preserving history; implement real batched portable FakeIP fsync/CRC journal with strict restart integrity."}
```
