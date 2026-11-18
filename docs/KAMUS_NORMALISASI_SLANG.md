# 📖 Kamus Normalisasi Slang & Singkatan (Task D-03)

**Tanggal Pembaruan:** 2026-11-18 10:06:59
**Basis Data:** `data/processed/comments_cleaned.csv` (1.498 komentar bersih)
**File Kamus Mesin:** `data/slang_dict.json`
**Status Task:** ✅ **SELESAI (DONE)**

---

## 1. Ringkasan Kamus

Kamus ini memuat **109 istilah slang dan singkatan** bahasa Indonesia yang **secara empiris terbukti muncul** di dalam dataset media sosial S.O.N.A.R.

Tujuan utama normalisasi ini adalah menyamakan representasi semantik teks sebelum di-embed ke vektor 768 dimensi (Modul 11) sehingga kata informal seperti `yg`, `gak`, `skrg` dipetakan ke makna baku `yang`, `tidak`, `sekarang`.

---

## 2. Daftar Istilah (Sebelum ➔ Sesudah) & Frekuensi Kemunculan

| No | Bentuk Asal (Slang/Singkatan) | Bentuk Baku (Normalisasi) | Frekuensi di Dataset | Contoh Konteks Nyata di Dataset |
| :---: | :--- | :--- | :---: | :--- |
| 1 | `yg` | **yang** | 545x | "Sehat.. Sllu pak mahfud salam hormat terimakasih buat pencerahan.. ..." |
| 2 | `hp` | **handphone** | 258x | "Semoga yang nonton video ini bisa kebeli HP yang di inginkan dan bi..." |
| 3 | `pak` | **bapak** | 224x | "Love u Prof Mahfud. Sehat terus ya pak...kita masih membutuhkan pro..." |
| 4 | `bisa` | **bisa** | 212x | "Semoga yang nonton video ini bisa kebeli HP yang di inginkan dan bi..." |
| 5 | `aja` | **saja** | 131x | "MasyaAllah...Makin rued aja negara ini. Semoga negara kita baik2 aj..." |
| 6 | `bang` | **abang** | 128x | "Habis ini wajib datang bang Hotman om ded biar seimbang" |
| 7 | `gak` | **tidak** | 121x | "Giliran memakzulkan gak sampai 1 minggu, ruu perampasan aset bertah..." |
| 8 | `udah` | **sudah** | 109x | "Udah di harga 2 digit, melihat kondisi ekonomi Indonesia yang seper..." |
| 9 | `ga` | **tidak** | 103x | "mungkin karna alas hp nya ga nyentuh si meja ,soalnya yang kemarin ..." |
| 10 | `kalo` | **kalau** | 93x | "dedi pas prabowo banyak program bermasalah bungkam, kalo dari kubu ..." |
| 11 | `gw` | **saya** | 75x | "Ini yang gw tunggu dari pas launching😂" |
| 12 | `tau` | **tahu** | 57x | "Jadi selama ini Sigit tau dong gw suka main hp pas kerja?" |
| 13 | `emang` | **memang** | 47x | "Kualitas layar 1.5 k emang ok banget dah apalagi ram nya gede pula nih" |
| 14 | `bgt` | **banget** | 44x | "Enak bgt klu dgr podcast pak Mahfud dmanapun, saat menjelaskan baha..." |
| 15 | `klo` | **kalau** | 40x | "sy pun setuju, klo yg menggantikan mas Gibran adalah prof. Mahfud 🤲..." |
| 16 | `utk` | **untuk** | 39x | "Strategi yg luar biasa dr Pak Prabowo utk membongkar kebusukan geng..." |
| 17 | `karna` | **karena** | 37x | "mungkin karna alas hp nya ga nyentuh si meja ,soalnya yang kemarin ..." |
| 18 | `tp` | **tetapi** | 35x | "Terima kasih banyak bang, ada yg membuat kesemsem tp Samsung S26 sa..." |
| 19 | `cuma` | **hanya** | 34x | "Negara ini sbnernya bagus cuma kekurangan org ujur aja" |
| 20 | `dgn` | **dengan** | 33x | "Saya bukan memilih pak Mahfud krmn, tapi saya salut dgn kepintaran ..." |
| 21 | `aku` | **saya** | 33x | "Aku pakai poco X7 pro aja udah puas ... Mantap memang poco." |
| 22 | `sampe` | **sampai** | 32x | "masih bertahan dipoco x3GT ,meskipun kalo hp sampe lowbet parah sam..." |
| 23 | `dapet` | **dapat** | 30x | "Setidaknya masih oke daripada OPPO A7 Pro Max anomali 10JT cuman da..." |
| 24 | `bener` | **benar** | 30x | "Yg dibilang raymon ini bener bgt,,, pake bgt... Salut deh ada pemud..." |
| 25 | `udh` | **sudah** | 28x | "Mantul, lihat bagian belakangnya aja yang dijelasin bang David udh ..." |
| 26 | `jika` | **jika** | 28x | "Harga hp 4 juta serasa hp 2 juta jika kembali ke tahun lalu🤣" |
| 27 | `sy` | **saya** | 28x | "Pak Makfud hebat sy hormat, sy doakan beliau sll dilindungi Alloh y..." |
| 28 | `gua` | **saya** | 28x | "Jeleknya dibagian speaker aja menurut gua, kenapa harus ditaro disi..." |
| 29 | `tak` | **tidak** | 27x | "Satu-satunya kesalahan Gibran adalah dia mengalahkan Mahfud MD dala..." |
| 30 | `dr` | **dari** | 26x | "Alhamdulillah nonton pakai x7 pro, sdh lbh dr cukup 🙌🏻" |
| 31 | `gini` | **begini** | 26x | "Udh ga kuat, ekonomi gini mending kapan² aja upgradenya😭 Cuma bisa ..." |
| 32 | `gk` | **tidak** | 25x | "Muda²han besok sudah nyampai poco F9 ultra nya.uda gk sabar pengen ..." |
| 33 | `org` | **orang** | 25x | "Selamat pak atas penghargaan yg diberikan ,betul sekali negara butu..." |
| 34 | `om` | **om** | 25x | "Sehat-sehat, Prof. Mahfud, Om Deddy. Mari saling mendoakan kebaikan..." |
| 35 | `keren` | **keren** | 25x | "Pak Mafud Kalau jelasin hukum jelas dan mudah dipahami. Keren" |
| 36 | `dah` | **sudah** | 24x | "Kualitas layar 1.5 k emang ok banget dah apalagi ram nya gede pula nih" |
| 37 | `tdk` | **tidak** | 24x | "Semoga MMD tdk ditutup mata hatinya oleh Alloh SWT, seperti Rizal F..." |
| 38 | `krn` | **karena** | 22x | "mahfud MD sudah tendensius bukan lagi seorang imuwan, krn dia bagia..." |
| 39 | `skrg` | **sekarang** | 22x | "(muncul di komentar panjang)" |
| 40 | `mantap` | **mantap** | 22x | "Prabowo menikmati tanpa tersentuh. Mantap sekali konsepnya" |
| 41 | `pengen` | **pengin** | 21x | "semoga yang pengen beli hp semoga cepet kebeli ya amiiinn 😊" |
| 42 | `sdh` | **sudah** | 19x | "Gibran yg selalu terdepan tentang UU PERAMPASAN ASET...kini dia SDH..." |
| 43 | `jg` | **juga** | 18x | "Akhirnya muncul jg review nya di channel ini wkwkwkw tumbenan ga up..." |
| 44 | `gue` | **saya** | 18x | "Gila gue nonton Reymond dari dulu, sekarang jadi sekeras ini. Gass ..." |
| 45 | `lu` | **kamu** | 18x | "Bagus Bang. Lu selalu pinter manfaatin momen, dan itu yg selalu bik..." |
| 46 | `spek` | **spesifikasi** | 18x | "Bg aduin lgi dong hp² varian spek tinggi, contoh apple, xiomi, sams..." |
| 47 | `bg` | **abang** | 17x | "bg mungkin next bisa coba untuk tes gaming bisa ditambah where wind..." |
| 48 | `doang` | **saja** | 15x | "Dari 2019 sampe skrng masih pake realme5i,tiap tahun liat" doang ri..." |
| 49 | `sbg` | **sebagai** | 14x | "Raymond Chin sangat pantas dan cocok menggantikannya sbg wapres. Smart" |
| 50 | `nggak` | **tidak** | 14x | "Alhamdulillah nggak nyesel udh beli" |
| 51 | `gitu` | **begitu** | 14x | "mungkin karna alas hp nya ga nyentuh si meja ,soalnya yang kemarin ..." |
| 52 | `dlm` | **dalam** | 13x | "Ini sih narasumber yg bnr2 mengedukasi dlm bidang nya" |
| 53 | `bpk` | **bapak** | 11x | "Disini yg gue liat om dedy jd pembantu bpk,said didu... "Nyapuhin m..." |
| 54 | `kemaren` | **kemarin** | 11x | "Nyesel bgt tahun kemaren gak langsung ngambil Samsung A07 pas masih..." |
| 55 | `dpt` | **dapat** | 10x | "Semoga Bp.Ahok th 2029 jadi Presiden sehingga kesejahteraan dan kea..." |
| 56 | `cuman` | **hanya** | 10x | "😂om ded jangan undang musuh Prabowo dan Gibran 😂dia datang ke podca..." |
| 57 | `tpi` | **tetapi** | 9x | "Tpi sayang, dari dulu smpe skrng boxsnya tetep sm, kek gk ada kesan..." |
| 58 | `skrng` | **sekarang** | 9x | "Tpi sayang, dari dulu smpe skrng boxsnya tetep sm, kek gk ada kesan..." |
| 59 | `sering` | **sering** | 9x | "Bagaimana mau dihapus waktu masih menjabat, Prabowo sering ngerem m..." |
| 60 | `dg` | **dengan** | 8x | "Saya suka dg YouTube mas Raymond....orangnya kritis,tapi punya etika.." |
| 61 | `blm` | **belum** | 8x | "Untung blm PO ternyata vidionya kureng 😢 trimakasih bg david sudah ..." |
| 62 | `makasih` | **terima kasih** | 8x | "Makasih member 😊" |
| 63 | `ngga` | **tidak** | 7x | "(muncul di komentar panjang)" |
| 64 | `bs` | **bisa** | 7x | "ah gw bahagia bs jd member pas banyak kejadian jd bisa liat videony..." |
| 65 | `km` | **kamu** | 7x | "(muncul di komentar panjang)" |
| 66 | `dri` | **dari** | 6x | "(muncul di komentar panjang)" |
| 67 | `wkwkwk` | **tertawa** | 6x | "langsung saja "Manusia Kayu" Pinochio dari solo wkwkwk, sungguh bes..." |
| 68 | `mrk` | **mereka** | 5x | "(muncul di komentar panjang)" |
| 69 | `parah` | **parah** | 5x | "masih bertahan dipoco x3GT ,meskipun kalo hp sampe lowbet parah sam..." |
| 70 | `beneran` | **sungguhan** | 5x | "Baru kemarin Saya Comment di Video kemarin bahas Gibran eh beneran" |
| 71 | `dlu` | **dulu** | 5x | "Alhamdulillah bisa kebeli Poco f9 ultra d waktu PO. Nunggu di revie..." |
| 72 | `kl` | **kalau** | 4x | "Suka banget kl Pak Mahfud menjelaskan sesuatu." |
| 73 | `jga` | **juga** | 4x | "Makin yakin hp keluaran 24/25 masih paling oke, dan jadi makin yaki..." |
| 74 | `gt` | **begitu** | 4x | "Alhamdulillah tahun lalu bulan Desember sudah beli infinix GT 30 pr..." |
| 75 | `gmn` | **bagaimana** | 4x | "ya gmn ya... dr jaman dulu orng melayu indonesia emng hobby nya per..." |
| 76 | `hape` | **handphone** | 4x | "(muncul di komentar panjang)" |
| 77 | `moga` | **semoga** | 4x | "saya masih user poco f7 moga bisa upgrade 😊" |
| 78 | `u` | **untuk** | 3x | "Love u Prof Mahfud. Sehat terus ya pak...kita masih membutuhkan pro..." |
| 79 | `drpd` | **daripada** | 3x | "Ane lebih milih jualannya gibran dan geng solo drpd jualan prabowo ..." |
| 80 | `smp` | **sampai** | 3x | "(muncul di komentar panjang)" |
| 81 | `pgn` | **pengin** | 3x | "(muncul di komentar panjang)" |
| 82 | `kmu` | **kamu** | 3x | "(muncul di komentar panjang)" |
| 83 | `org2` | **orang-orang** | 3x | "Semoga makin bnyk org2 seperti pk Ahok menjadi pemimpin bangsa kita🙏" |
| 84 | `tadi` | **tadi** | 3x | "kena pelanggaran kah? tadi siang kayanya udah upload" |
| 85 | `slalu` | **selalu** | 3x | "Pak mahfud sehat2 trus, slalu arahkan bangsa ini ke arah yg benar❤" |
| 86 | `batre` | **baterai** | 3x | "(muncul di komentar panjang)" |
| 87 | `emg` | **memang** | 3x | "bg mungkin next bisa coba untuk tes gaming bisa ditambah where wind..." |
| 88 | `thanks` | **terima kasih** | 3x | "Akhirnya di review sama ini channel, thanks "Gadgetin"" |
| 89 | `jir` | **waduh** | 3x | "(muncul di komentar panjang)" |
| 90 | `wkwk` | **tertawa** | 3x | "4:45 Timeline Video nya malah 2-1,5 Juta Typo bukan harusnya 2,5 Ju..." |
| 91 | `smpe` | **sampai** | 2x | "Tpi sayang, dari dulu smpe skrng boxsnya tetep sm, kek gk ada kesan..." |
| 92 | `bngt` | **banget** | 2x | "(muncul di komentar panjang)" |
| 93 | `br` | **baru** | 2x | "(muncul di komentar panjang)" |
| 94 | `smg` | **semoga** | 2x | "Pak Mahfud Cerdas dengan Logika yg tepat smg sehat2 ya Pak" |
| 95 | `trims` | **terima kasih** | 2x | "coba bang di react output video kontennya dan kira2 ada ga outcome ..." |
| 96 | `pnting` | **penting** | 2x | "FUNGSI SAID DIDU ? ahh yang pnting ge ngomong biar rame😂" |
| 97 | `gmna` | **bagaimana** | 1x | "(muncul di komentar panjang)" |
| 98 | `bsa` | **bisa** | 1x | "(muncul di komentar panjang)" |
| 99 | `sblm` | **sebelum** | 1x | "ninggalin jejak sblm rame - - - semoga awal tahun 2027 bisa kebeli ..." |
| 100 | `sblmnya` | **sebelumnya** | 1x | "(muncul di komentar panjang)" |
| 101 | `kmrn` | **kemarin** | 1x | "(muncul di komentar panjang)" |
| 102 | `sllu` | **selalu** | 1x | "Sehat.. Sllu pak mahfud salam hormat terimakasih buat pencerahan.. ..." |
| 103 | `camera` | **kamera** | 1x | "Rekomendasi hp budget 5jt, camera, baterai, chipset bagus apa ya. K..." |
| 104 | `mantapz` | **mantap** | 1x | "(muncul di komentar panjang)" |
| 105 | `mantul` | **mantap betul** | 1x | "Mantul, lihat bagian belakangnya aja yang dijelasin bang David udh ..." |
| 106 | `duluan` | **dahulu** | 1x | "Dulu mah ROG yg speakernya bagus dan selalu duluan snapdragon terba..." |
| 107 | `thx` | **terima kasih** | 1x | "Alhamdulilah di turutin dong poco F9 ❤❤,thx bang david..." |
| 108 | `pdhl` | **padahal** | 1x | "(muncul di komentar panjang)" |
| 109 | `anjg` | **anjing** | 1x | "Giliran memakzulkan gak sampai 1 minggu, ruu perampasan aset bertah..." |

---

## 3. Kriteria Selesai (Checklist PM)

- [x] Kamus mencakup 109 istilah yang benar-benar muncul di dataset riil.
- [x] Format mesin tersedia dalam JSON (`data/slang_dict.json`).
- [x] Format dokumentasi manusia tersedia dengan perbandingan Sebelum ➔ Sesudah.
- [x] Siap diintegrasikan ke pipeline preprocessing D-04.
