# firmware_backup

อิมเมจ flash เดิมที่อ่านออกมาจากบอร์ดก่อนเขียนทับด้วย `IODebug`

## lift2_original_firmware.hex

โปรแกรมเดิมบนบอร์ด **Lift 2** อ่านออกมาเมื่อ 30 ส.ค. 2026 ก่อนอัปโหลด IODebug
(~14,063 ไบต์ของโค้ดจริง) — เป็นโปรแกรมของทีมอื่นที่ถอดรหัสตำแหน่งลิฟต์อยู่แล้ว
เอาต์พุตตัวอย่างอยู่ใน `lift2_original_serial_output.txt`:

```
Binary: 000010  Decimal: 2
  COIL1: 1
  COIL2: 1
```

`Decimal: 2` ตรงกับตารางสอบเทียบของเรา (รหัส 2 = ป้ายชั้น 1) ยืนยันว่าโปรแกรมเดิม
ใช้การเข้ารหัสไบนารี 6 บิตแบบเดียวกัน ส่วน COIL1/COIL2 เป็นสัญญาณที่ทีมนั้นแยกไว้
ซึ่งยังไม่รู้ว่าตรงกับขาไหนในแผนที่ของเรา

### กู้คืนโปรแกรมเดิม

```
avrdude -C <path>/avrdude.conf -c wiring -p m2560 -P COM3 -b 115200 \
        -U flash:w:firmware_backup/lift2_original_firmware.hex:i
```
