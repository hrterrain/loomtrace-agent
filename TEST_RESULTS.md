# LoomTrace – Test Results

Run on 11 Nov 2026, 11:39 · **15/15 passed**

| ID | What it tests | Input (product · place · weaver / batch) | Expected | Got | Re-plans | Reason | Result |
|---|---|---|---|---|---|---|---|
| T01 | Authentic Kancheepuram silk, full details | Kancheepuram Silk · Kancheepuram, Tamil Nadu · WV-KAN-002 / B-KAN-0020 | Supported | Supported | 0 | all checks passed | ✅ |
| T02 | Local name 'Kanjivaram' (agent re-plans to resolve alias) | Kanjivaram Silk Saree · Thiruvallur, Tamil Nadu · WV-KAN-001 / B-KAN-0010 | Supported | Supported | 1 | all checks passed | ✅ |
| T03 | Authentic Pochampalli ikat | Pochampally Ikat Saree · Nalgonda, Telangana · WV-POC-003 / B-POC-0030 | Supported | Supported | 1 | all checks passed | ✅ |
| T04 | Authentic Banarasi saree | Banarasi Silk Saree · Varanasi, Uttar Pradesh · WV-BAN-006 / B-BAN-0060 | Supported | Supported | 1 | all checks passed | ✅ |
| T05 | New product: Sambalpuri ikat (Odisha) | Sambalpuri Ikat Saree · Bargarh, Odisha · WV-SAM-002 / B-SAM-0020 | Supported | Supported | 1 | all checks passed | ✅ |
| T06 | New product: Muga silk (state-wide GI, Assam) | Muga Silk Mekhela · Sualkuchi, Assam · WV-MUG-001 / B-MUG-0010 | Supported | Supported | 1 | all checks passed | ✅ |
| T07 | New product: Kota Doria (Rajasthan) | Kota Doria Saree · Kaithoon, Rajasthan · WV-KTD-004 / B-KTD-0040 | Supported | Supported | 1 | all checks passed | ✅ |
| T08 | Fake: Banarasi claimed from Surat, Gujarat | Banarasi Silk Saree · Surat, Gujarat · WV-BAN-002 / B-BAN-0020 | Conflicting evidence | Conflicting evidence | 1 | failed: region_in_gi_area, state_matches | ✅ |
| T09 | Fake: Kancheepuram sold with an Ikat weaver's ID | Kancheepuram Silk · Kancheepuram, Tamil Nadu · WV-POC-004 / B-POC-0040 | Conflicting evidence | Conflicting evidence | 0 | failed: weaver_cluster, batch_weaver_match | ✅ |
| T10 | Fake: batch woven by a different weaver | Pochampalli Ikat · Nalgonda, Telangana · WV-POC-001 / B-POC-0050 | Conflicting evidence | Conflicting evidence | 0 | failed: batch_weaver_match | ✅ |
| T11 | Fake: Kancheepuram 'silk' made of polyester | Kancheepuram Silk · Kancheepuram, Tamil Nadu · WV-KAN-002 / B-KAN-0020 | Conflicting evidence | Conflicting evidence | 0 | failed: material_consistent | ✅ |
| T12 | Fake: Chanderi claimed from Varanasi | Chanderi Saree · Varanasi, Uttar Pradesh · WV-CHA-001 / B-CHA-0010 | Conflicting evidence | Conflicting evidence | 1 | failed: region_in_gi_area, state_matches | ✅ |
| T13 | Missing weaver and batch details | Banaras Brocades and Sarees · Varanasi, Uttar Pradesh · — / — | Insufficient evidence | Insufficient evidence | 0 | missing: weaver_registered, weaver_cluster, batch_found, batch_weaver_match | ✅ |
| T14 | Weaver ID not in any registry | Kota Doria · Kota, Rajasthan · WV-XXX-999 / B-KTD-0010 | Insufficient evidence | Insufficient evidence | 0 | missing: weaver_registered, weaver_cluster, batch_weaver_match | ✅ |
| T15 | Batch ID not on record | Kullu Shawl · Kullu, Himachal Pradesh · WV-KUL-003 / B-KUL-9999 | Insufficient evidence | Insufficient evidence | 1 | missing: batch_found, batch_weaver_match | ✅ |
