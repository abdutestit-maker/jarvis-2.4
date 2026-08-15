// Generates minimal valid PNG icons for Tauri (no external deps).
import { deflateSync } from 'node:zlib';
import { writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const OUT = join(process.cwd(), 'src-tauri', 'icons');
mkdirSync(OUT, { recursive: true });

function crc32(buf) {
  let c, crc = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    c = (crc ^ buf[i]) & 0xff;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    crc = (crc >>> 8) ^ c;
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length, 0);
  const t = Buffer.from(type, 'ascii');
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(Buffer.concat([t, data])), 0);
  return Buffer.concat([len, t, data, crc]);
}
function makePNG(size) {
  const sig = Buffer.from([137,80,78,71,13,10,26,10]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0); ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  const row = Buffer.alloc(1 + size * 4);
  const raw = Buffer.concat(Array.from({length: size}, () => {
    row[0] = 0;
    for (let x = 0; x < size; x++) {
      // dark teal glass color with a soft cyan rim
      const t = x / size;
      row[1 + x*4] = 20 + Math.round(40 * (1 - Math.abs(t - 0.5) * 2));
      row[1 + x*4+1] = 30 + Math.round(120 * (1 - Math.abs(t - 0.5) * 2));
      row[1 + x*4+2] = 40 + Math.round(180 * (1 - Math.abs(t - 0.5) * 2));
      row[1 + x*4+3] = 255;
    }
    return Buffer.from(row);
  }));
  const idat = deflateSync(raw);
  return Buffer.concat([sig, chunk('IHDR', ihdr), chunk('IDAT', idat), chunk('IEND', Buffer.alloc(0))]);
}

const sizes = [32, 128, 256];
for (const s of sizes) {
  const png = makePNG(s);
  writeFileSync(join(OUT, `${s}x${s}.png`), png);
}
// 128x128@2x
writeFileSync(join(OUT, '128x128@2x.png'), makePNG(256));

// ICO container wrapping a 32x32 PNG + 256x256 PNG
function makeICO() {
  const png32 = makePNG(32);
  const png256 = makePNG(256);
  const entries = [];
  const images = [];
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0); header.writeUInt16LE(1, 2); header.writeUInt16LE(2, 4);
  const dirs = [png32, png256];
  const sizesArr = [32, 256];
  let offset = 6 + dirs.length * 16;
  for (let i = 0; i < dirs.length; i++) {
    const d = Buffer.alloc(16);
    d[0] = sizesArr[i] === 256 ? 0 : sizesArr[i];
    d[1] = sizesArr[i] === 256 ? 0 : sizesArr[i];
    d[2] = 0; d[3] = 0;
    d.writeUInt16LE(1, 4); d.writeUInt16LE(32, 6);
    d.writeUInt32LE(dirs[i].length, 8);
    d.writeUInt32LE(offset, 12);
    entries.push(d);
    images.push(dirs[i]);
    offset += dirs[i].length;
  }
  return Buffer.concat([header, ...entries, ...images]);
}
writeFileSync(join(OUT, 'icon.ico'), makeICO());

console.log('Icons generated:', sizes.map(s => `${s}x${s}.png`).join(', '), '128x128@2x.png, icon.ico');
