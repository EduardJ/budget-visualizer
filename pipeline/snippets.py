"""Highlighted crops of the printed rows behind references: one grayscale JPEG per ref, written as <out_dir>/<rid>.jpg."""
import io, pathlib, pypdfium2 as pdfium
from PIL import ImageDraw
def render(refs, ids, pdf_path, out_dir, scale=1.35, above=22, below=26, width=880, quality=42):
    """refs: {rid: ref with page and top (pt)}; crops the full page width from `above` pt over the row to `below` pt under it"""
    out_dir=pathlib.Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    for f in out_dir.glob('*.jpg'): f.unlink()
    pdf=pdfium.PdfDocument(str(pdf_path))
    SC=scale; cache={}; size=0
    for rid in sorted(ids,key=lambda r:(refs[r]['page'],refs[r]['top'])):
        r=refs[rid]; p=r['page']
        if p not in cache:
            cache.clear()
            pg=pdf[p-1]; img=pg.render(scale=SC).to_pil().convert('L'); cache[p]=img
        img=cache[p]; W,H=img.size
        top=r['top']*SC
        y0=max(0,top-above*SC); y1=min(H,top+below*SC)
        crop=img.crop((0,int(y0),W,int(y1))).convert('RGB')
        d=ImageDraw.Draw(crop,'RGBA'); hy=top-y0
        d.rectangle([0,hy-2*SC,W,hy+10*SC],fill=(255,214,0,70),outline=(200,150,0,160))
        if W>width: crop=crop.resize((width,int(crop.size[1]*width/W)))
        b=io.BytesIO(); crop.convert('L').save(b,'JPEG',quality=quality,optimize=True)
        (out_dir/f'{rid}.jpg').write_bytes(b.getvalue()); size+=len(b.getvalue())
    return len(ids),size
