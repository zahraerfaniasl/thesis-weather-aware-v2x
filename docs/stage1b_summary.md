# مرحله ۱b: برگشت LiDAR به ۸۵ متر

## نتیجه در یک نگاه
- برد LiDAR خودرو و RSU به ۸۵ متر برگشت، مثل V2Xverse اصلی.
- `pmin` برابر `9.8515e-05` شد و برد مؤثر RF2 حدود ۲۲٫۶ و RF3 حدود ۱۰٫۸ متر است.
- جدول fog تا ۸۶ متر ساخته و با دقت ماشینی با مرجع Hahner اعتبارسنجی شد.
- نمونه‌گیر باران ۱٫۸ برابر سریع‌تر شد و خروجی‌اش بیت‌به‌بیت با نسخه‌ی قبلی برابر است.
- جمع‌آوری داده روی سرور اجرا نشده است. مدل‌های فعلی با داده‌ی ۱۲ متری آموزش دیده‌اند، پس این configها تا پیش از آموزش مجدد نباید برای نتیجه‌گیری اجرا شوند.

## تغییرات
شاخه: `stage1b-lidar85`، ساخته‌شده از `stage1-weather-calibration`. پسوند backup: `.before_stage1b_lidar85`.

| فایل | تغییر | backup |
|---|---|---|
| `simulation/leaderboard/leaderboard/autoagents/agent_wrapper.py:187` | `range` از ۱۲ به ۸۵ | دارد |
| `simulation/leaderboard/leaderboard/sensors/fixed_sensors.py:565` | `range` از ۱۲ به ۸۵ | دارد |
| ۱۸ فایل `pnp_config_stage9b_{baseline,density}_seed2029_closed_loop_{OFF,RF2,RF3}_{5_10,5_50,8_10}.yaml` | `pmin: 9.8515e-05` و `manifest_path` جدید | دارد |
| `opencood/data_utils/augmentor/joint_weather_rain_sampler_stage9b.py` | برداری‌سازی | دارد |
| `scripts/stage1_weather_offline_test.py` | پیش‌فرض‌های ۸۵ متر | دارد |
| `opencood/data_utils/augmentor/joint_weather_tables_r86/` | جدول‌ها و manifest جدید | ندارد (جدید) |
| `scripts/stage1b_build_fog_tables.py` | سازنده‌ی جدول | ندارد (جدید) |
| `scripts/stage1b_rain_parity_test.py` | تست برابری | ندارد (جدید) |
| `scripts/stage1b_collect_43routes.sh` | جمع‌آوری | ندارد (جدید) |
| `scripts/stage1b_dataset_qa.py` | QA | ندارد (جدید) |
| `docs/stage1_summary.md` | اصلاح جمله‌ی fog clutter و ذکر `fixed_sensors.py` | در git |

جدول‌ها داخل مخزن‌اند، چون `results/` نباید بازنویسی شود. فایل‌های `npz` در `.gitignore` هستند و با `git add -f` ثبت شدند، پس هنگام `rsync` نباید حذف شوند.

## جاهایی که ۱۲ متر فرض شده است
| مورد | وضعیت |
|---|---|
| جدول fog قدیمی با `target_range_max_m=13` | برای ابر ۸۵ متری خطا می‌دهد. configهای حلقه‌بسته به جدول جدید اشاره می‌کنند. |
| `config.yaml` مدل‌های `stage9b_confirm3_*` با `pmin=2.25e-05` و manifest قدیمی | دست نخورد. config آموزش جدید باید `pmin` و `manifest_path` جدید را صریحاً بگیرد. |
| `checkpoints` و `opencood/logs/stage9b_*` | با داده‌ی ۱۲ متری آموزش دیده‌اند و با برد جدید سازگار نیستند. |
| `results/stage9b7_raw` و `results/stage9b7_index` | داده‌ی ۱۲ متری. دست نخورد. |
| `scripts/stage9b15_refresh_index.py`، `stage9b15b_refresh_test_index.py`، `stage9b16_dataset_qa.py`، `stage9b31_finalize_dataset.sh` | مسیر `stage9b7` در آن‌ها ثابت است. **برای داده‌ی جدید اجرا نشوند**؛ `stage9b15` پیوندهای index قدیمی را پاک می‌کند. برای مرحله‌ی بعد باید نسخه‌ی index جدید نوشته شود. |
| `scripts/stage1_weather_offline_test.py` | به‌روز شد. |
| `docs/stage1_summary.md` و `docs/stage1_results/` | سند تاریخی مرحله‌ی ۱ با ۱۲ متر است. |
| `CLAUDE.md` (یافته‌ی ۱) | هنوز `pmin≈6.6e-3` را می‌گوید و تغییر داده نشد. |

بدون تغییر و بدون مشکل: `cav_lidar_range` همان `[-36,-12,36,12]` است، و `max_voxel_train=32000` با بیشینه‌ی ۱۵٬۶۸۵ pillar در فریم‌های نمونه‌ی ۸۵ متری کافی است.

**محدودیت این فهرست:** دیسک ADATA حین کار جدا شد، پس جست‌وجو فقط روی کد مخزن کامل شد و configهای داخل `results/stage9b_pipeline` بررسی نشدند.

## جدول fog
`pmin = exp(-0.004·85)/85² = 9.8515e-05`. ساخت هر سه profile با ۸۶۱ گره حدود ۹ ثانیه طول کشید.

| اعتبارسنجی | گره | خطای برد قله | خطای نسبی انتگرال |
|---|---|---|---|
| جدول ذخیره‌شده‌ی RF1 / RF2 / RF3 (۰ تا ۱۳ m) | ۱۳۱ | ۰ | کمتر از `3.4e-16` |
| lookup اصلی Hahner با α=0.03 / 0.06 / 0.2 (۰ تا ۸۶ m) | ۸۶۱ | ۰ | کمتر از `2.2e-16` |

| profile | SHA-256 (ابتدا) |
|---|---|
| RF1 | `35ca8e069dc8` |
| RF2 | `8b0dd918d258` |
| RF3 | `a06a4e60bc64` |

## تست آفلاین با جدول نهایی
۶ فریم ego و ۶ فریم RSU از zip شهر Town05. این فریم‌ها فقط برای بررسی‌اند و هیچ پارامتری با آن‌ها تنظیم نشد. نتیجه با `pmin=9.8515e-05`:

| شرط | برد مؤثر (m) | حذف ego | حذف RSU | rain در ego / RSU (جمع ۶ ابر) | fog |
|---|---|---|---|---|---|
| OFF | ۸۵ | ۰٪ | ۰٪ | ۰ / ۰ | ۰ |
| RF1 | ۳۲٫۵ | ۱۲٫۳٪ | ۱۳٫۷٪ | ۴۷۹ / ۱۰۷۹ | ۰ |
| RF2 | ۲۲٫۶ | ۱۹٫۴٪ | ۲۳٫۵٪ | ۹۵۸ / ۲۲۷۸ | ۰ |
| RF3 | ۱۰٫۸ | ۴۰٫۶٪ | ۵۸٫۳٪ | ۹۶۳ / ۲۸۵۶ | ۰ |

Self-test مصنوعی با مقدار تحلیلی یکی بود و OFF بدون تغییر ماند. `fog` صفر می‌ماند و مه فقط زیر `pmin≈2.2e-5` ظاهر می‌شود.

## نمونه‌گیر باران
**روش:** جریان تصادفی به همان ترتیب نسخه‌ی قبلی خوانده می‌شود. توان قطره با برد کم و با قطر کم نمی‌شود، پس `pow/log/exp` فقط روی قطره‌هایی اجرا می‌شود که ممکن است قوی‌ترین باشند.

| معیار | نتیجه |
|---|---|
| ۱۵۳ بررسی (۱۷ مورد × ۳ شرط × ۳ seed) | ۰ اختلاف |
| تست فشار (بافر کوچک، guard پهن، `rmin`، نرخ کم) | ۶۴ بررسی، ۰ اختلاف |
| معیار برابری | بایت‌به‌بایت روی چهار خروجی و حالت نهایی `RandomState` |
| زمان کل روی مک | ۱۱۴٫۸ ثانیه به ۶۳٫۷ ثانیه (۱٫۸۰ برابر) |

چون برداری‌سازی ساده فقط ۱٫۰۴ برابر سریع‌تر بود، حذف قطره‌های غیرممکن اضافه شد. این آزمایش با numpy 1.26 روی مک انجام شد و باید با نسخه‌ی numpy سرور هم تکرار شود.

**اصلاح برآورد قبلی:** گفته بودم با سریع‌سازی، ران نهایی نزدیک ۱۳۳ ساعت می‌ماند. با سرعت واقعی، سربار باران حدود ۱٫۵۵ برابر حالت ۱۲ متری است و این حدود ۲۰ تا ۲۵ ساعت به ران نهایی اضافه می‌کند. این هنوز برآورد است. جدول fog هم ۹ ثانیه طول کشید، نه ۴ دقیقه.

## دستورات سرور
**سرور:** تست برابری، قبل از هر چیز:

```bash
cd /home/user/V2Xverse && PYTHONPATH=/home/user/V2Xverse /home/user/miniconda/envs/v2x_client/bin/python scripts/stage1b_rain_parity_test.py --seeds 3 --inputs "results/stage9b7_index/val/*/ego_vehicle_0/lidar/005*.npy"
```

**سرور:** جمع‌آوری ۴۳ route با CARLA روشن روی پورت 2000:

```bash
cd /home/user/V2Xverse && nohup bash scripts/stage1b_collect_43routes.sh > results/stage1b_collect_console.log 2>&1 &
```

**سرور:** QA بعد از جمع‌آوری:

```bash
cd /home/user/V2Xverse && /home/user/miniconda/envs/v2x_client/bin/python scripts/stage1b_dataset_qa.py --raw-root results/stage1b_raw --report results/stage1b_qa.tsv --full-radar
```

- **فهرست route:** اسکریپت آن را روی سرور از `results/stage9b7_index/*/dataset_index.txt` می‌سازد و اگر ۳۰ / ۶ / ۷ نباشد متوقف می‌شود.
- **Preflight:** اگر `range=12` در دو فایل سنسور باشد یا فضای آزاد کمتر از ۶۰ GB باشد، شروع نمی‌کند.
- **ادامه‌پذیری:** اجرای دوباره route‌های موفق را رد می‌کند. هر route تا ۳ بار تلاش می‌شود (`STAGE1B_MAX_ATTEMPTS`).
- **شرط پذیرش:** همان شرط‌های جمع‌آوری اصلی. دور قبل از ۲۱۹ تلاش فقط ۴۲ مورد موفق شد، پس ممکن است بعضی route‌ها با ۳ تلاش تمام نشوند. جایگزینی route هم خودکار نیست و تصمیم شماست.
- **زمان و حجم:** حدود ۲۷ تا ۳۵ ساعت و تقریباً ۳۳ GB (برآورد).

**QA:** با داده‌ی مصنوعی ساخته‌شده از فریم‌های ۸۵ متری تست شد: نمونه‌ی سالم پاس شد، و نمونه‌های ۱۲ متری، رادار کهنه، فریم رادار ناقص و تعداد route ناکافی رد شدند. اسکریپت جمع‌آوری فقط `bash -n` را گذرانده و اجرا نشده است. پوشه‌ی `simulation/leaderboard/data/scenarios` در git نیست و روی مک فایل‌های لازم را ندارد؛ اسکریپت روی سرور وجود هر فایل را چک می‌کند.

## قدم بعد
1. تست برابری روی سرور، سپس جمع‌آوری و QA.
2. نوشتن index جدید برای `results/stage1b_raw`.
3. آموزش مجدد، که تغییر بزرگ است و تأیید جدا می‌خواهد.
