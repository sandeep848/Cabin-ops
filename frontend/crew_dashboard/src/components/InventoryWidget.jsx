import React from 'react';
import { capitalize, inventoryStockClass } from './Helpers';

export default function InventoryWidget({ inventory, inventoryRestocking, restockItem }) {
  return (
    <div className="sidebar-section">
      <div className="section-label">Galley Inventory</div>
      {inventory.length === 0 ? (
        <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>No inventory data</div>
      ) : (
        <div className="inventory-list">
          {inventory.map((inv) => (
            <div className="inventory-row" key={inv.item}>
              <span className="inventory-name" title={inv.alternative ? `Alt: ${inv.alternative}` : ''}>
                {capitalize(inv.item)}
              </span>
              <span className={`inventory-count ${inventoryStockClass(inv.stock)}`}>
                {inv.stock}
              </span>
              <button
                className="btn-restock"
                disabled={inventoryRestocking === inv.item}
                onClick={() => restockItem(inv.item)}
              >
                {inventoryRestocking === inv.item ? '…' : '+10'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
