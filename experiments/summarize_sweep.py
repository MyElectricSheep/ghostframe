"""Render the completed final sweep as Markdown tables."""
import json
from statistics import median

from experiments.final_sweep import OUT


def load(name, count):
    rows=json.loads((OUT/f"{name}.json").read_text())
    if len(rows)!=count:
        raise ValueError(f"Expected {count} records in {name}.json")
    return rows


def table(headers, rows):
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        print("| " + " | ".join(map(str,row)) + " |")
    print()


def count(values):
    return f"{sum(values)}/{len(values)}"


def detector(pairs, protocol):
    flags=[]
    for i,(clean,marked) in enumerate(pairs):
        training=pairs[:i]+pairs[i+1:]
        if protocol:
            threshold=(max(a for a,_ in training)+min(b for _,b in training))/2
            direction=1
        else:
            values=sorted({value for pair in training for value in pair})
            thresholds=[values[0]-1,*((a+b)/2 for a,b in zip(values,values[1:])),values[-1]+1]
            def accuracy(hypothesis):
                t,d=hypothesis
                return sum((d*(a-t)<0)+(d*(b-t)>=0) for a,b in training)
            threshold,direction=max(((t,d) for t in thresholds for d in (1,-1)),key=accuracy)
        flags.append((direction*(clean-threshold)>=0,direction*(marked-threshold)>=0))
    return count([a for a,_ in flags]),count([b for _,b in flags])


def main():
    sweep=load("results",14)
    fresh=[r for r in sweep if r["fresh"]]
    assert len(fresh)==4
    print("## Final measurements\n\n### Resize and compression\n")
    records=[]
    for label in sweep[0]["cases"]:
        cases=[r["cases"][label] for r in sweep]
        fresh_cases=[r["cases"][label] for r in fresh]
        if "authenticated" in cases[0]:
            records.append((label,"—","—",count([c["authenticated"] for c in cases]),
                            count([c["authenticated"] for c in fresh_cases]),"—"))
        else:
            wide=count([c["wide"]["authenticated"] for c in cases]) if "wide" in cases[0] else "—"
            records.append((label,count([c["hard"] for c in cases]),count([c["soft"] for c in cases]),wide,
                            count([c["soft"] for c in fresh_cases]),median(c["byte_errors"] for c in cases)))
    table(("Condition","Known dimensions, hard","Known dimensions, confidence erasures",
           "Geometry search","Fresh covers, best oracle or search for combined case","Median wrong bytes"),records)
    print("### Exposure search\n")
    rows=load("exposure",14)
    table(("Condition","Direct","Exposure search","Median search time"),
          [(label,count([r["cases"][label]["direct"] for r in rows]),
            count([r["cases"][label]["search"]["authenticated"] for r in rows]),
            f"{median(r['cases'][label]['search']['seconds'] for r in rows):.2f} s") for label in rows[0]["cases"]])
    print("### Detection\n")
    table(("Detector and channel","Clean flagged","Marked flagged","Fresh clean flagged","Fresh marked flagged"),
          [(label,*detector([r["detection"][label] for r in sweep],"protocol" in label),
            *detector([r["detection"][label] for r in fresh],"protocol" in label))
           for label in sweep[0]["detection"]])
    print("The fresh-only detector column uses three fresh training pairs per fold.\n")
    print("### Search timing\n")
    rows=load("speed",3)
    assert all(r["reference"]["authenticated"]==r["optimized"]["authenticated"] for r in rows)
    table(("Cover","Full phase map","Aligned blocks","Authenticated in both"),
          [(r["cover"],f"{r['reference']['seconds']:.2f} s",f"{r['optimized']['seconds']:.2f} s",
            r["reference"]["authenticated"] and r["optimized"]["authenticated"]) for r in rows])
    print("### Cover selection\n")
    rows=load("cover-selection",112)
    groups=[[r for r in rows if r["trial"]==trial] for trial in range(8)]
    records=[]
    for length in (2,4,8,16):
        distinct=[len({r["clean"][:length] for r in group if r["clean"][:length]==r["jpeg70"][:length]})
                  for group in groups]
        records.append((length,f"{min(distinct)}–{max(distinct)}",
                        f"{median(distinct)/(2**length):.4%}"))
    table(("Bits","Distinct stable prefixes per key","Median exact target coverage"),records)
    print("### Fresh neural covers\n")
    rows=load("neural-holdout",16)
    records=[]
    for epsilon in (2,8):
        for length in (16,32):
            group=[r for r in rows if r["epsilon"]==epsilon and len(r["target"])==length]
            records.append((epsilon,length,count([r["cases"]["png"]["errors"]==0 for r in group]),
                            count([r["cases"]["jpeg70_420"]["errors"]==0 for r in group]),
                            count([r["cases"][k]["errors"]==0 for r in group
                                   for k in ("center91","offset89","offset93")])))
    table(("RGB levels","Bits","PNG exact","JPEG 70 exact","Crop exact"),records)


if __name__=="__main__":
    main()
