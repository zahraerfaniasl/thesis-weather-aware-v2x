# مرحله ۱: کالیبراسیون آب‌وهوای LiDAR

## نتیجه در یک نگاه
- `pmin` از `2.25e-05` به **`0.006619`** تغییر کرد، در هر ۱۸ config حلقه‌بسته و برای هر دو روش یکسان.
- مشکل `lost=0` حل شد: در RF2 و RF3 نقاط واقعاً حذف می‌شوند و برد مؤثر با محاسبه‌ی تحلیلی می‌خواند.
- **`fog=0` حل نشد و با هیچ `pmin`ی حل نمی‌شود.** `rain` هم به صفر رسید. پس مدل در عمل یک برش برد به‌همراه تضعیف شدت است، نه مدل clutter.
- این `pmin` یک فرض مدل‌سازی است، نه واقعیت فیزیکی یک LiDAR تجاری (بخش ۳).
- تست کامل روی val و اجرای حلقه‌بسته هنوز انجام نشده است.

## ۱. تأیید منطق انتخاب return
فایل‌ها: `joint_weather_return_core_stage9b.py`، `joint_weather_cloud_stage9b.py`، `joint_weather_rain_sampler_stage9b.py`، `joint_weather_bridge_stage9b.py`.

برای هر نقطه سه کاندیدا ساخته می‌شود:

| کاندیدا | توان |
|---|---|
| hard | `I·exp(-2αr)/r²` |
| rain | قوی‌ترین قطره‌ی نمونه‌گیری‌شده (LISA، `strongest`) |
| fog | `I·integral·β/β0` (معادل Hahner تقسیم بر `r²`) |

سپس `argmax` برنده را تعیین می‌کند و نقطه فقط اگر توان برنده `>= pmin` باشد می‌ماند؛ در غیر این صورت `lost` است. این منطق با کد مرجع LISA یکی است.

یافته‌های تأییدشده:
- `2.25e-05` دقیقاً `0.9/200²` است، یعنی مقدار پیش‌فرض LISA با `rmax=200`. این مقدار برای یک LiDAR ۲۰۰ متری است، در حالی که داده‌ی ما تا ۱۲ متر است.
- شدت CARLA بازتاب‌پذیری نیست و فقط تابع برد است: `I=exp(-0.004r)` (خطای کمتر از `7e-8` روی ۱۲ فریم). پس آستانه‌ی `pmin` یک برش برد قطعی می‌سازد، نه حذف تصادفی.
- `pmin` در `config.yaml` مدل است و از `stage9b_joint_weather_override` در config agent قابل بازنویسی است (`pnp_agent_e2e.py:266`)، پس به `opencood/logs/` دست نخورد.

## ۲. روش کالیبراسیون
**تعریف:** `pmin` توان بازگشتی هدف در مرز برد سنسور در هوای صاف است:

`pmin = I(R_max)/R_max² = exp(-0.004·12)/12² = 6.619e-3`

برد مؤثر از حل `exp(-(2α+0.004)r)/r² = pmin` به دست می‌آید. به این ترتیب OFF بدون تغییر می‌ماند.

| گزینه‌ی `pmin` | مقدار | RF1 (m) | RF2 (m) | RF3 (m) | نظر |
|---|---|---|---|---|---|
| فعلی، LISA با `rmax=200` | `2.25e-5` | 44.6 | 29.6 | 13.4 | بیشتر از ۱۲ m، پس `lost=0` |
| LISA با `rmax=85` | `1.25e-4` | 30.7 | 21.5 | 10.4 | فقط RF3 اثر دارد |
| LISA با `rmax=12` | `6.25e-3` | 9.2 | 7.6 | 4.75 | فرمول منبع، بازتاب ۰٫۹ |
| **انتخابی** `I(12)/12²` | `6.619e-3` | **9.0** | **7.5** | **4.7** | با شدت واقعی CARLA سازگار |

برآورد اولیه‌ی شما (۷٫۵ و ۴٫۷ متر) درست بود. اختلاف دو گزینه‌ی آخر کمتر از ۰٫۲ متر است، پس انتخاب بین آن‌ها نتیجه را عوض نمی‌کند.

## ۳. مقایسه با منابع و محدودیت‌ها
**LISA (Kilic et al., arXiv:2107.07004):** در `pylisa/lisa.py` داریم `Pmin = 0.9·rmax⁻²`. روش ما همان ایده است: آستانه از برد اسمی سنسور می‌آید. فقط ضریب ۰٫۹ با `I(12)=0.953` جایگزین شده است.

**Hahner (ICCV 2021, arXiv:2108.05249):** این روش آستانه‌ی آشکارسازی ندارد. در `fog_simulation.py` شدت hard با `exp(-2αr)` کم و گرد می‌شود، و fog فقط اگر از hard قوی‌تر باشد جایگزین می‌شود. نقطه‌ی hard هرگز حذف نمی‌شود. پس حذف نقطه از LISA می‌آید، نه Hahner.

**چرا `fog=0` می‌ماند:** بیشینه‌ی توان fog در RF2 برابر `1.09e-5` و در RF3 برابر `2.36e-5` است، ولی توان hard در ۱۲ متر حتی در RF3 برابر `4.91e-5` است. پس داخل ۱۲ متر hard همیشه `argmax` را می‌برد، مستقل از `pmin`. این نتیجه‌ی ساختاری برد ۱۲ متر است، نه باگ. گزارش مرجع `fog_reference_run` هم در α=0.06 صفر پاسخ fog دارد.

**چرا آستانه‌ی جدا برای fog نگذاشتم:** گیرنده‌ای که hard با توان `4.9e-5` را نبیند ولی fog با `2.4e-5` را ببیند از نظر فیزیکی قابل دفاع نیست.

**محدودیت اصلی:** این کالیبراسیون سنسور را کوتاه‌برد با حاشیه‌ی توان صفر در ۱۲ متر فرض می‌کند. یک LiDAR واقعی با برد ۲۰۰ متر در RF3 حدود ۱۳ متر می‌بیند، یعنی `lost=0` برای چنین سنسوری در محدوده‌ی ۱۲ متر درست بود. برد ۴٫۷ متر پس حاصل این فرض است و باید در مقاله صریح گفته شود. داور ممکن است بپرسد که آیا این فرض به نفع رادار است یا نه.

**یافته‌ی جدید، برد LiDAR:** داده‌ی اصلی V2Xverse در zip تا ۸۵ متر است (`rmax≈85`، `I_min≈0.712`)، ولی داده‌ی stage9b، `agent_wrapper.py:187` و `fixed_sensors.py:565` برد ۱۲ متر دارند، در حالی که محدوده‌ی ادراک `x∈[-36,36]` است. پس LiDAR فقط حدود یک‌سوم طولی محدوده‌ی ادراک را می‌بیند، حتی در OFF. دلیل این انتخاب در مخزن ثبت نشده است و تغییری در آن ندادم.

## ۴. نتیجه‌ی تست آفلاین
اسکریپت: `scripts/stage1_weather_offline_test.py`، با کلاس اصلی `ExperimentalJointWeather` و بررسی hash جدول‌ها. خروجی خام: `docs/stage1_results/`.

Self-test مصنوعی پاس شد: برد مشاهده‌شده ۸٫۹۹ / ۷٫۴۸ / ۴٫۶۸ متر برابر مقدار تحلیلی بود و OFF بدون تغییر ماند.

**Town04 val، فریم 0051 (۱ فریم ego + ۱ فریم RSU، برد بومی ۱۲ m)، با `pmin=0.006619`:**

| شرط | ego حذف % | RSU حذف % | برد بیشینه‌ی خروجی (m) | rain | fog |
|---|---|---|---|---|---|
| OFF | 0.0 | 0.0 | 12.00 | 0 | 0 |
| RF1 | 19.9 | 23.8 | 8.99 | 0 | 0 |
| RF2 | 34.3 | 63.4 | 7.48 | 0 | 0 |
| RF3 | 70.5 | 83.9 | 4.67–4.68 | 0 | 0 |

با `pmin` قبلی روی همین فریم‌ها حذف در همه‌ی شرایط ۰٪ بود، که یافته‌ی ۱ را بازتولید می‌کند.

**Town05 از zip (۶ ego + ۶ RSU، داده‌ی ۸۵ متری بریده‌شده به ۱۲ m)، میانگین حذف با بازه:**

| شرط | ego حذف % | RSU حذف % |
|---|---|---|
| RF1 | 14.7 (11–17) | 59.7 (38–74) |
| RF2 | 24.9 (21–27) | 77.9 (55–94) |
| RF3 | 63.7 (60–66) | 87.5 (78–97) |

هیچ پارامتری از این فریم‌ها تنظیم نشد؛ `pmin` تحلیلی است. با این حال Town05 شهر ارزیابی است و این جدول فقط برای بررسی است.

**اعتبار نتایج:** نمونه کوچک است (Town04 فقط یک جفت فریم، چون فریم‌های `stage9b7_index` روی دیسک ADATA فایل خالی‌اند). درصد حذف به هندسه‌ی صحنه وابسته است، ولی برد مؤثر قطعی است.

**اثر روی RSU:** کف زمین در فریم RSU حدود `z=-7.7` است. با فرض همین ارتفاع، سر عابر (۱٫۸ متر) حدود ۵٫۹ متر پایین‌تر از سنسور است، پس در RF3 با برد ۴٫۷ متر LiDAR RSU عابر را اصلاً نمی‌بیند. این استنتاج هندسی است و روی عابر واقعی اندازه‌گیری نشده است.

## ۵. فایل‌های تغییرکرده
روی شاخه‌ی `stage1-weather-calibration`:

| فایل | تغییر | backup |
|---|---|---|
| ۱۸ فایل `pnp_config_stage9b_{baseline,density}_seed2029_closed_loop_{OFF,RF2,RF3}_{5_10,5_50,8_10}.yaml` | افزودن `pmin: 0.006619` به override | `.before_stage1_pmin` |
| `opencood/data_utils/augmentor/joint_weather_bridge_stage9b.py` | ثبت `pmin` در `JOINT_WEATHER_TRACE` | `.before_stage1_pmin` |
| `scripts/stage1_weather_offline_test.py` | جدید | ندارد |
| `docs/stage1_summary.md`، `docs/stage1_results/*.json` | جدید | ندارد |

بررسی شد: در هر ۹ سلول (شرط × اندازه) override دو روش یکسان است، syntax با گرامر Python 3.7 پاس شد و ادغام override با `validate_joint_weather` مقدار `0.006619` را می‌دهد. `agent_wrapper.py`، `results/`، `checkpoints/` و `opencood/logs/` تغییر نکردند.

نکته برای مرحله‌ی ۳: `pmin` در `config.yaml` مدل‌های قبلی همان `2.25e-05` است، پس config آموزش جدید باید صریحاً `0.006619` بگیرد.

## ۶. کارهای باقی‌مانده روی سرور
**سرور:** تست کامل روی val (نه Town05):

```bash
cd /home/user/V2Xverse && PYTHONPATH=/home/user/V2Xverse /home/user/miniconda/envs/v2x_client/bin/python scripts/stage1_weather_offline_test.py --manifest results/stage9b_weather_reference/joint_response_tables_unshifted_20260909_120940/manifest.json --root results/stage9b7_index/val --frames-per-agent 5 --pmin 2.25e-5 6.619e-3 --out results/stage1_weather_offline_val.json
```

ستون `empty` تعداد ابرهای زیر ۱۰۰ نقطه را نشان می‌دهد. در ۱۴ ابر تست‌شده صفر بود، ولی رفتار voxelizer با ابر خالی روی مک قابل تست نبود (spconv ندارد). قبل از ران بزرگ، یک مسیر RF3 خارج از مجموعه‌ی ارزیابی نهایی به‌عنوان smoke test اجرا شود و در لاگ `JOINT_WEATHER_TRACE` مقدار `"pmin": 0.006619` و `lost>0` دیده شود.

## ۷. متن کوتاه برای بخش روش مقاله
> We degrade LiDAR with a joint rain–fog model that combines the fog response of Hahner et al. [ICCV 2021] with the strongest-return rain model of LISA [Kilic et al., 2021] under additive extinction, α = α_rain + α_fog. For each ray, the hard-target, strongest-droplet and fog-peak candidates are compared, and the strongest is kept only if its power exceeds a detection threshold P_min; otherwise the point is lost. Following LISA, P_min is tied to the nominal sensor range, here using the CARLA intensity model: P_min = exp(−0.004 R_max)/R_max² = 6.62×10⁻³ for R_max = 12 m. Clear-air returns are therefore unaffected, and the effective hard-target range falls to 7.5 m in RF2 (50 mm/h, α_fog = 0.06 m⁻¹) and 4.7 m in RF3 (50 mm/h, α_fog = 0.20 m⁻¹). This threshold models a short-range sensor with no link margin at R_max and is not calibrated to a specific commercial LiDAR; at this sensitivity, the simulated degradation consists of range loss and intensity attenuation, with no rain or fog clutter returns. The same weather and threshold are applied to the ego and RSU LiDARs for all compared methods.

## قدم بعد
قبل از مرحله‌ی ۲ باید درباره‌ی برد LiDAR تصمیم گرفته شود:

- **ماندن روی ۱۲ متر:** همین تغییرات کافی است و نیازی به جمع‌آوری مجدد داده نیست، ولی محدودیت بخش ۳ در مقاله می‌ماند.
- **برگشت به ۸۵ متر:** محدوده‌ی ادراک پوشش داده می‌شود و clutter باران برمی‌گردد. clutter مه برنمی‌گردد: با `pmin` کالیبره‌شده‌ی `9.85e-5`، مقدار `fog` همچنان صفر است و مه فقط زیر `pmin≈2.2e-5` ظاهر می‌شود. این گزینه به جمع‌آوری مجدد داده، ساخت جدول fog تا برد بیشتر و آموزش مجدد نیاز دارد، که تغییر بزرگی است و تأیید شما را می‌خواهد.
