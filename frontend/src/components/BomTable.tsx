// frontend/src/components/BomTable.tsx
import type { BOM } from '../types'

export function BomTable({ bom }: { bom: BOM }) {
  return (
    <div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: '#333', color: 'white' }}>
            {['Category', 'Part', 'Model', 'Qty', 'Unit', 'Extended', 'Source'].map(h => (
              <th key={h} style={{ padding: '6px 10px', textAlign: 'left' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bom.items.map((item, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #eee', background: i % 2 ? '#fafafa' : 'white' }}>
              <td style={{ padding: '5px 10px' }}>{item.category}</td>
              <td style={{ padding: '5px 10px' }}>{item.part}</td>
              <td style={{ padding: '5px 10px' }}>{item.manufacturer} {item.model}</td>
              <td style={{ padding: '5px 10px' }}>{item.qty}</td>
              <td style={{ padding: '5px 10px' }}>${item.unit_price.toFixed(2)}</td>
              <td style={{ padding: '5px 10px' }}>${item.extended_price.toFixed(2)}</td>
              <td style={{ padding: '5px 10px' }}>
                {item.source_url
                  ? <a href={item.source_url} target="_blank" rel="noopener noreferrer">Buy</a>
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          {Object.entries(bom.subtotals).map(([cat, total]) => (
            <tr key={cat} style={{ fontWeight: 'bold', background: '#f5f5f5' }}>
              <td colSpan={5} style={{ padding: '4px 10px', textAlign: 'right', textTransform: 'capitalize' }}>{cat}</td>
              <td style={{ padding: '4px 10px' }}>${total.toFixed(2)}</td>
              <td />
            </tr>
          ))}
          <tr style={{ fontWeight: 'bold', fontSize: 15, background: '#e8d5a3' }}>
            <td colSpan={5} style={{ padding: '6px 10px', textAlign: 'right' }}>Grand Total</td>
            <td style={{ padding: '6px 10px' }}>${bom.grand_total.toFixed(2)}</td>
            <td />
          </tr>
        </tfoot>
      </table>
      <div style={{ margin: '12px 0', padding: '12px 14px', background: '#f9f9f9',
                    borderLeft: '4px solid #333', fontSize: 13, lineHeight: 1.5 }}>
        {bom.rationale}
      </div>
    </div>
  )
}
