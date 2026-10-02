"""Deterministic monthly KPI calculation. No AI/API required at runtime."""
import argparse
import calendar
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re


def calculate(config, reports):
    targets, weights = config['targets'], config['weights']
    if not math.isclose(sum(weights.values()), 1, abs_tol=1e-12):
        raise ValueError('KPI weights must sum to one')
    if targets['discount_zero'] <= targets['discount']:
        raise ValueError('Discount zero-point threshold must exceed target')
    excluded = set(config['excluded'])
    names = [n for n, shift in config['roster'].items() if shift in ('AM', 'PM') and n not in excluded]
    unknown = set(reports['beverage']) - set(config['roster']) - excluded
    if unknown:
        raise ValueError('Update roster or exclusions for: ' + ', '.join(sorted(unknown)))
    active = [n for n in names if any(n in reports[k] for k in reports)]
    missing = [(n, k) for n in active for k in reports if n not in reports[k]]
    if missing:
        raise ValueError(f'Missing employee/report pairs: {missing}')
    net = sum(reports['sales'][n]['net_sales'] for n in active)
    covers = sum(reports['sales'][n]['covers'] for n in active)
    if net <= 0 or covers <= 0:
        raise ValueError('Included team requires positive sales and covers')
    ppa_goal = net / covers
    result = []
    for n in active:
        sales, bev, turns = (reports[k][n] for k in ('sales', 'beverage', 'turns'))
        if min(sales['net_sales'], sales['covers'], bev['net_sales'], turns['avg_minutes'], turns['checks']) <= 0:
            raise ValueError(f'Invalid denominator for {n}')
        beverage = bev['beverage_sales'] / bev['net_sales']
        discount = sales['discount'] / sales['net_sales']
        ppa = sales['net_sales'] / sales['covers']
        goal = targets['beverage_am' if config['roster'][n] == 'AM' else 'beverage_pm']
        components = {
            'beverage': min(100, beverage / goal * 100),
            'discount': max(0, min(100, (targets['discount_zero'] - discount) / (targets['discount_zero'] - targets['discount']) * 100)),
            'minutes': min(100, targets['minutes'] / turns['avg_minutes'] * 100),
            'ppa': min(100, ppa / ppa_goal * 100),
        }
        score = sum(components[k] * weights[k] for k in weights)
        flagged = discount >= targets['discount'] or turns['avg_minutes'] >= targets['minutes']
        tier = 4 if score < config['tiers']['3'] else 3 if flagged or score < config['tiers']['2'] else 2 if score < config['tiers']['1'] else 1
        result.append(dict(employee=n, shift=config['roster'][n], net_sales=sales['net_sales'], covers=sales['covers'], beverage=beverage, discount=discount, avg_minutes=turns['avg_minutes'], checks=turns['checks'], ppa=ppa, components=components, score=score, tier=tier))
    return dict(ppa_target=ppa_goal, net_sales=net, covers=covers, employees=sorted(result, key=lambda r: (-r['score'], r['employee'])), absent=sorted(set(names)-set(active)))


def load_reports(folder, month, location):
    import openpyxl
    year, mon = map(int, month.split('-'))
    expected = [date(year, mon, 1), date(year, mon, calendar.monthrange(year, mon)[1])]
    specs = {'beverage': ('BRGIHOP Employee Contest Detail', 5, 1, [2, 3, 4]), 'sales': ('Employee Sales Statistics', 6, 1, [2, 3, 5, 7, 9, 10]), 'turns': ('Server Table Turn Stats', 6, 0, [3, 4, 5, 6])}
    reports, sources = {}, []
    for kind, (prefix, start, name_col, sum_cols) in specs.items():
        matches = []
        for file in Path(folder).glob('*.xlsx'):
            if not file.name.startswith(prefix):
                continue
            wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
            sheet = wb.active
            rows = list(sheet.values)
            wb.close()
            dates = [date(int(y), int(m), int(d)) for m, d, y in re.findall(r'(\d{1,2})/(\d{1,2})/(\d{4})', str(rows[0][0]))]
            if dates == expected:
                matches.append((file, sheet.title, rows))
        if len(matches) != 1:
            raise ValueError(f'{month}: expected one {kind} file, found {len(matches)}')
        file, sheet_name, rows = matches[0]
        if str(rows[1][0]).replace(' ', '') != f'Location:{location}':
            raise ValueError(f'Wrong restaurant: {file.name}')
        if kind == 'sales' and (rows[2][0] != 'Dayparts: All' or rows[3][0] != 'Departments: All'):
            raise ValueError('Sales filters must be All dayparts / All departments')
        if kind == 'turns' and rows[2][0] != 'Departments: Eat In':
            raise ValueError('Table turns department must be Eat In')
        if kind == 'beverage' and rows[3][2] != 'Eat In Beverage %':
            raise ValueError('Beverage contest must be Eat In')
        total_idx = next((i for i in range(start, len(rows)) if rows[i][name_col] in ('Total', 'Totals')), None)
        if total_idx is None:
            raise ValueError('Missing totals row')
        body = rows[start:total_idx]
        if len({r[name_col] for r in body}) != len(body):
            raise ValueError('Duplicate employees')
        for col in sum_cols:
            if abs(sum(r[col] for r in body) - rows[total_idx][col]) > .005:
                raise ValueError(f'Unreconciled total: {file.name}, column {col+1}')
        parsed = {}
        for r in body:
            n = r[name_col]
            if kind == 'sales':
                parsed[n] = dict(net_sales=r[2], covers=r[3], discount=r[5])
                if r[3] and not math.isclose(r[2]/r[3], r[4], abs_tol=1e-8):
                    raise ValueError(f'PPA mismatch: {n}')
            elif kind == 'beverage':
                parsed[n] = dict(beverage_sales=r[2], net_sales=r[4])
                if r[4] and not math.isclose(r[2]/r[4], r[5], abs_tol=1e-8):
                    raise ValueError(f'Beverage rate mismatch: {n}')
            else:
                parsed[n] = dict(avg_minutes=r[7], checks=r[6])
                if r[6] and not math.isclose(r[3]/r[6], r[7], abs_tol=1e-8):
                    raise ValueError(f'Time mismatch: {n}')
        reports[kind] = parsed
        sources.append(dict(file=file.name, sheet=sheet_name, sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    return reports, sources


def write_report(result, month, output, previous=None):
    output = Path(output) / month
    output.mkdir(parents=True, exist_ok=True)
    prev = {r['employee']:r for r in previous['employees']} if previous else {}
    lines = [f'# Server performance — {month}', '', f"Included team: {len(result['employees'])}. Weighted PPA target: ${result['ppa_target']:.2f}.", '', '| Server | Shift | Net sales | Beverage | Discount | Avg mins | PPA | Score | Tier | Change |', '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    text = [f'Desempeño de servidores — {month}', f"PPA objetivo: ${result['ppa_target']:.2f}. Servidores incluidos: {len(result['employees'])}.", '']
    for r in result['employees']:
        change = f"{r['score']-prev[r['employee']]['score']:+.2f}" if r['employee'] in prev else '—'
        lines.append(f"| {r['employee']} | {r['shift']} | ${r['net_sales']:,.2f} | {r['beverage']:.2%} | {r['discount']:.2%} | {r['avg_minutes']:.2f} | ${r['ppa']:.2f} | {r['score']:.2f} | {r['tier']} | {change} |")
        text.append(f"• {r['employee']}: {r['score']:.2f} pts; nivel {r['tier']}.")
    text += ['', 'Top 5 en ventas netas (sin puntos adicionales al ranking KPI):']
    for r in sorted(result['employees'],key=lambda r:(-r['net_sales'],r['employee']))[:5]:
        text.append(f"• {r['employee']}: ${r['net_sales']:,.2f}")
    text += ['', f"Ventas netas del grupo incluido: ${result['net_sales']:,.2f}.", 'Ventas sin ajuste por horas trabajadas. Tiempo de cuentas con tarjeta incluidas; cuentas >3 horas excluidas. Revisar antes de publicar.']
    lines += ['', 'Net sales does not add KPI points. No adjustment for hours worked. Previous-month scores use current rules and roster.', '', '## Sources', '']
    lines += [f"- {s['file']} ({s['sheet']}), SHA-256 {s['sha256']}" for s in result.get('sources',[])]
    (output/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    # Long reports remain a text attachment instead of silently truncating.
    (output/'telegram.txt').write_text('\n'.join(text),encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--month', required=True, help='YYYY-MM')
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', default='outputs', type=Path)
    parser.add_argument('--previous-input', type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    reports, sources = load_reports(args.input,args.month,config['location'])
    result = calculate(config,reports)
    result.update(month=args.month,sources=sources,config_sha256=hashlib.sha256(args.config.read_bytes()).hexdigest())
    previous = None
    if args.previous_input:
        y,m = map(int,args.month.split('-'))
        prev_month = f'{y if m>1 else y-1:04d}-{m-1 if m>1 else 12:02d}'
        p,_ = load_reports(args.previous_input,prev_month,config['location'])
        previous=calculate(config,p)
    print(write_report(result,args.month,args.output,previous))


if __name__ == '__main__':
    main()
