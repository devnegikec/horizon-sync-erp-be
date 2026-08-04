Inbound ANS Management :-

Pilot assumption: Each saleable product and master carton carries a unique QR code that can be scanned and validated by WMS.

SAP will remain the source system for the stock-transfer/outbound document and ASN. The relevant document and expected item details will be made available in WMS through the agreed SAP connector; controlled CSV upload may be used during the pilot if required.

At the mother warehouse, WMS will support scan-based picking, verification and dispatch against the SAP document. At the retail warehouse, the operator will scan the received products against the ASN. WMS will identify matched, short, excess, damaged or rejected items, generate the receiving record and complete the warehouse receipt after the configured approval process.

ASN processing is a standard WMS capability. SAP integration and document mapping will be implemented as part of the pilot integration scope.

Inbound Good Receipt:-

"WMS will receive the ASN details and the unique product identities before physical receipt. During goods receipt, operators will scan each box /package using an Android handheld device and validate it against the expected ASN.

Received items can be classified as accepted, damaged, rejected, excess or pending inspection. Rejected or damaged items will be moved to a designated rejection/quarantine location and will not be treated as available inventory. Items confirmed as dispatched but not received will remain associated with the relevant ASN as in-transit or shortage quantities until the discrepancy is resolved.

The final receipt status and approved quantities will be updated in SAP through the agreed integration. The exact approval, rejection and transit-discrepancy workflow will be finalized during process design."

Put away :-

"Directed putaway is supported through Android handheld devices. The operator scans the unique product QR code and the destination location QR code, creating an item-to-location association in WMS.

WMS can recommend the preferred bin or storage location based on configured rules such as warehouse zone, product category, available capacity, storage compatibility, existing stock and location priority. Authorized users may select an alternate location where the business process permits.

Warehouse layout, location master, capacity and putaway rules will be configured for the mother warehouse and retail warehouse during the pilot."

Inventory Management, Inventory Visibility:-

WMS provides real-time operational inventory visibility by warehouse, zone, aisle, line, rack, bin, SKU, unique product identity and stock status.

Users can view available, allocated, picked, packed, in-transit, rejected, damaged and quarantine inventory, together with the current location and movement history of each uniquely identified product. Dashboard and warehouse-layout visualization will be configured based on the approved location master.

SAP will continue to maintain enterprise stock records, while WMS will maintain detailed warehouse-location and execution visibility and synchronize agreed inventory movements with SAP.

Inventory Management Cycle Counting :-


WMS supports scheduled, ABC-based, location-based, SKU-based and ad hoc cycle counting using compatible Android handheld devices.

The system can generate count tasks, support blind or visible counting, record recounts and route variances through a configured approval workflow. Approved inventory adjustments will be communicated to SAP through the agreed integration.

Count frequency, variance tolerance, approval levels and device specifications will be finalized during pilot configuration.

Outbound Picking :-

Order Allocation

Optimal picking based on PO is standard feature in the WMS, wave, zone and pick-to-light are not applicable to Prestige warehouse scenario or use-case

Basic packing verification is supported in WMS. The operator can validate the picked products against the outbound order before shipment confirmation and maintain the association between products, cartons or handling units where applicable.

Customer-specific cartonization logic, automatic carton recommendation, packing-material management, weighing-device integration, printer integration and specialized label formats may require additional configuration or custom development after detailed requirement assessment.

For the pilot, the packing scope should be limited to scan-based packing verification and agreed label output unless advanced cartonization requirements are separately confirmed.

outboudn Shipping:-
WMS will support shipment staging, final scan verification, dispatch confirmation and shipment-status update for the pilot warehouses.

Before dispatch, the operator can validate the unique product identities and quantities against the relevant outbound document. The confirmed shipment details will be communicated to SAP through the agreed integration.

Direct integration with a TMS, transporter portal, carrier API, e-way bill service or transit-pass service depends on the selected service provider, available APIs and finalized business scope. Such third-party integrations will be assessed and estimated separately unless explicitly included in the pilot.
