# AOEM Battle Simulator

Simulator pertempuran lineup hero untuk eksperimen build, komparasi win rate, dan analisis performa skill.

Project ini mendukung:
- Simulasi detail 1 kali battle.
- Simulasi Monte Carlo (ribuan iterasi).
- Konfigurasi lineup fleksibel (termasuk custom skill per hero, per lineup).

## Fitur Utama

- Engine pertempuran berbasis tick.
- Evaluasi statistik lineup (might, armor, strategy, siege).
- Tracking hasil battle: pemenang, durasi, sisa pasukan.
- Monte Carlo runner untuk estimasi win rate yang lebih stabil.
- Report dashboard + averaged report.
- Override skill hero per lineup tanpa mengubah database hero global.

## Kebutuhan

- Python 3.11+

Lihat requirement versi Python di `pyproject.toml`.

## Struktur Project

```text
.
├── main.py                  # Entry point CLI simulator
├── benchmark.py             # Benchmark performa engine
├── pyproject.toml
├── README.md
├── data/
│   ├── heroes.json          # Database hero
│   └── skills.json          # Database skill
├── src/
│   ├── models.py            # Model domain + loader JSON
│   ├── mechanics.py         # Kalkulasi mekanik battle
│   ├── engine.py            # Battle engine inti
│   ├── runner.py            # MonteCarloRunner
│   ├── report.py            # Dashboard/report detail
│   └── averaged_report.py   # Ringkasan rata-rata hasil
└── tests/
    ├── test_engine.py
    └── test_runner.py
```

## Setup Cepat

1. Buat virtual environment:

```bash
python3 -m venv .venv
```

2. Aktifkan virtual environment:

```bash
source .venv/bin/activate
```

3. Jalankan simulator:

```bash
python main.py
```

Catatan:
- Saat ini project tidak punya dependency eksternal wajib, jadi tidak perlu install package tambahan.

## Cara Menjalankan

### 1) Detailed Mode (default)

Menjalankan 1 kali simulasi detail.

```bash
python main.py
```

Atau eksplisit:

```bash
python main.py --mode detailed
```

### 2) Monte Carlo Mode

Menjalankan banyak iterasi untuk estimasi win rate.

```bash
python main.py --mode monte-carlo --iterations 1000
```

Argumen CLI:
- `--mode`: `detailed` atau `monte-carlo` (default: `detailed`)
- `--iterations`: bilangan bulat positif, hanya dipakai di mode `monte-carlo` (default: `1000`)

## Konfigurasi Lineup di main.py

Lineup diatur di fungsi `main()` pada variabel `lineup_1_config` dan `lineup_2_config`.

Contoh paling sederhana (format lama, masih didukung):

```python
lineup_1_config = {
    "heroes": ["cyrus_the_great", "boudica", "mansa"],
    "troop_type": UnitType.PIKEMAN,
}
```

### Custom Skill Per Hero, Per Lineup (Fitur Baru)

Sekarang setiap slot hero bisa berupa object config, bukan hanya string hero key.

Format object hero:

```python
{
    "key": "hero_id",
    "custom_skills": ["skill_id_1", "skill_id_2"],
    "skill_overrides": {
        "custom_1": "skill_id_lain",
        "custom_2": None
    }
}
```

Penjelasan:
- `key`: ID hero dari `data/heroes.json`.
- `custom_skills` (opsional): mengganti seluruh slot custom hero (`custom_1`, `custom_2`, dst) untuk hero itu di lineup ini saja.
- `skill_overrides` (opsional): override slot spesifik, tetapi hanya untuk slot `custom_*`.
- Nilai `None` di `skill_overrides` artinya slot custom tersebut dihapus.

Kenapa ini penting:
- Kamu bisa test 2 lineup dengan hero yang sama, tapi kombinasi skill berbeda.
- Override tidak memodifikasi `HEROES_DB` global, jadi aman antar lineup.
- Skill dasar hero (`commander` dan `signature`) tidak bisa diubah karena sifatnya unik per hero.

### Contoh A/B Test Hero Sama, Skill Berbeda

```python
lineup_1_config = {
    "heroes": ["cyrus_the_great", "boudica", "mansa"],
    "troop_type": UnitType.PIKEMAN,
}

lineup_2_config = {
    "heroes": [
        "cyrus_the_great",
        {
            "key": "boudica",
            "custom_skills": ["fearless_retribution", "golden_odyssey"],
            # Opsional:
            # "skill_overrides": {"custom_2": None},
        },
        "mansa",
    ],
    "troop_type": UnitType.PIKEMAN,
}
```

Valid format slot di list `heroes`:
- `"hero_key"`
- object hero config (format di atas)
- `None` untuk empty slot

Jumlah slot hero harus tetap tepat 3.

## Template Skenario Cepat (Siap Copy)

Bagian ini dibuat supaya kamu bisa langsung eksperimen tanpa setup ulang format config.

Cara pakai:
1. Copy salah satu preset ke fungsi `main()`.
2. Assign ke `lineup_1_config` dan `lineup_2_config`.
3. Jalankan `python main.py --mode monte-carlo --iterations 1000`.
4. Bandingkan win rate dan survivability.

### Preset 1: Baseline Mirror

```python
lineup_1_config = {
  "heroes": ["cyrus_the_great", "boudica", "mansa"],
  "troop_type": UnitType.PIKEMAN,
}

lineup_2_config = {
  "heroes": ["cyrus_the_great", "boudica", "mansa"],
  "troop_type": UnitType.PIKEMAN,
}
```

Tujuan:
- Memastikan hasil awal seimbang sebelum eksperimen variasi skill.

### Preset 2: Hero Sama, Ganti Custom Skill Slot Tengah

```python
lineup_1_config = {
  "heroes": ["cyrus_the_great", "boudica", "mansa"],
  "troop_type": UnitType.PIKEMAN,
}

lineup_2_config = {
  "heroes": [
    "cyrus_the_great",
    {
      "key": "boudica",
      "custom_skills": ["fearless_retribution", "golden_odyssey"],
    },
    "mansa",
  ],
  "troop_type": UnitType.PIKEMAN,
}
```

Tujuan:
- Uji impact pergantian custom skill tanpa mengganti hero.

### Preset 3: Swap Custom Skill Slot

```python
lineup_1_config = {
  "heroes": ["cyrus_the_great", "boudica", "mansa"],
  "troop_type": UnitType.PIKEMAN,
}

lineup_2_config = {
  "heroes": [
    {
      "key": "cyrus_the_great",
      "skill_overrides": {"custom_1": "whirlwind_sweep"},
    },
    "boudica",
    "mansa",
  ],
  "troop_type": UnitType.PIKEMAN,
}
```

Tujuan:
- Uji dampak penggantian skill di slot custom tertentu tanpa mengganti hero.

### Preset 4: Disable Satu Slot Skill

```python
lineup_1_config = {
  "heroes": ["cyrus_the_great", "boudica", "mansa"],
  "troop_type": UnitType.PIKEMAN,
}

lineup_2_config = {
  "heroes": [
    "cyrus_the_great",
    {
      "key": "boudica",
      "skill_overrides": {"custom_2": None},
    },
    "mansa",
  ],
  "troop_type": UnitType.PIKEMAN,
}
```

Tujuan:
- Mengukur kontribusi slot skill tertentu dengan metode ablation test.

### Preset 5: Komposisi Hero Berbeda

```python
lineup_1_config = {
  "heroes": ["cyrus_the_great", "boudica", "mansa"],
  "troop_type": UnitType.PIKEMAN,
}

lineup_2_config = {
  "heroes": ["attila", "lubu", "mansa"],
  "troop_type": UnitType.CAVALRY,
}
```

Tujuan:
- Membandingkan effect komposisi hero + troop type secara bersamaan.

## Workflow Eksperimen yang Direkomendasikan

1. Mulai dari Preset 1 sebagai baseline.
2. Ganti satu variabel saja per eksperimen (misal hanya `custom_skills` hero slot 2).
3. Jalankan minimal 1000 iterasi per skenario.
4. Simpan hasil utama: `win rate`, `a_remaining`, `b_remaining`, `duration`.
5. Ulangi skenario yang menjanjikan dengan 5000-10000 iterasi untuk mengurangi noise acak.

## Matrix Eksperimen (Template)

Gunakan tabel ini untuk merencanakan skenario sebelum run.

| ID | Preset Dasar | Variabel Diubah | Nilai Perubahan | Hipotesis | Iterasi |
| --- | --- | --- | --- | --- | --- |
| E01 | Preset 1 | custom_skills (slot 2) | boudica: [fearless_retribution, golden_odyssey] | sustain naik, durasi naik | 1000 |
| E02 | Preset 1 | custom_1 (slot 1) | cyrus.custom_1 -> whirlwind_sweep | scaling damage berubah | 1000 |
| E03 | Preset 1 | disable skill | boudica.custom_2 -> None | output turun jika skill penting | 1000 |
| E04 | Preset 1 | troop_type | PIKEMAN -> CAVALRY | matchup berubah signifikan | 1000 |

Tips isi matrix:
- Ubah satu variabel per eksperimen agar dampaknya jelas.
- Tulis hipotesis sebelum run agar evaluasi lebih objektif.
- Naikkan iterasi setelah kandidat terbaik ditemukan.

## Template Catatan Hasil (Copy-Paste)

Setelah setiap eksperimen, simpan ringkasan hasil dalam format konsisten seperti ini:

```text
[E01] Date: YYYY-MM-DD
Config:
- Lineup A: cyrus_the_great | boudica | mansa (PIKEMAN)
- Lineup B: cyrus_the_great | boudica(custom: fearless_retribution,golden_odyssey) | mansa (PIKEMAN)
- Iterations: 1000

Result:
- Win Rate A: xx.xx%
- Win Rate B: xx.xx%
- Draw: xx.xx%
- Avg Remaining A: xxxxx
- Avg Remaining B: xxxxx
- Avg Duration: xx.x sec

Conclusion:
- Hipotesis: TERBUKTI / TIDAK TERBUKTI
- Keputusan: lanjut / drop / retest 5000 iterasi
```

Kalau kamu mau menyimpan histori eksperimen di repo, buat file `experiments.md` dan append hasil per ID (`E01`, `E02`, dst).

## Data Hero dan Skill

Sumber data:
- `data/heroes.json`
- `data/skills.json`

Tips:
- Pakai ID hero/skill persis sama seperti di JSON.
- Jika ID hero/skill tidak ditemukan, simulator akan melempar `ValueError` yang menjelaskan key yang salah.

## Menjalankan Test

Jalankan semua test:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

Test meliputi:
- Validasi loading database hero/skill.
- Validasi mekanik inti.
- Validasi integritas runner (lineup original tidak termutasi).

## Benchmark

Untuk ukur performa engine:

```bash
python benchmark.py
```

Default benchmark menjalankan 1000 simulasi dan menampilkan:
- Total durasi.
- Rata-rata waktu per simulasi (ms).

## Troubleshooting

- Error `Hero '...' not found in database.`
  - Pastikan hero key valid di `data/heroes.json`.

- Error `Skill '...' not found in database.`
  - Pastikan skill key valid di `data/skills.json`.

- Error slot override tidak diperbolehkan
  - Hanya slot `custom_*` yang bisa dioverride.
  - Slot `commander` dan `signature` bersifat unik dasar hero dan tidak bisa diubah.

- Error iterations harus positif
  - Gunakan `--iterations` > 0.

- Hasil simulasi terasa terlalu random
  - Naikkan iterasi Monte Carlo (misal 5000 atau 10000) untuk rata-rata lebih stabil.

## Pengembangan Lanjutan (Ide)

- Tambah mode seed random agar hasil reproducible.
- Tambah export hasil ke CSV/JSON.
- Tambah CLI argumen untuk inject lineup config dari file eksternal.
- Tambah test khusus untuk skenario custom skill override per lineup.
