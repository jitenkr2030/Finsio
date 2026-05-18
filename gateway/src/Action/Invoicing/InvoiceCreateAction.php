<?php

declare(strict_types=1);

namespace Finsio\Gateway\Action\Invoicing;

use Finsio\Gateway\Connector\DjangoBackendConnector;
use Fusio\Engine\ActionAbstract;
use Fusio\Engine\ContextInterface;
use Fusio\Engine\ParametersInterface;
use Fusio\Engine\RequestInterface;

/**
 * POST /api/v1/invoices
 *
 * Creates an invoice with line items, posts accounting entries
 * to both django-ledger and beancount, and optionally generates
 * a payment link via the unified payment layer.
 *
 * POST body:
 *   - customer_id    (required) Customer identifier
 *   - customer_email (required) Customer email address
 *   - customer_name  (required) Customer display name
 *   - line_items     (required) Array of {description, quantity, unit_price, tax_rate?, category?}
 *   - currency       (optional) ISO 4217, default USD
 *   - due_days       (optional) Days until due, default 30
 *   - auto_collect   (optional) Boolean, generate payment link
 *   - processor      (optional) Preferred payment processor
 *   - notes          (optional) Invoice notes
 *
 * Scopes: invoice, admin
 */
final class InvoiceCreateAction extends ActionAbstract
{
    public function __construct(
        private readonly DjangoBackendConnector $backend,
    ) {}

    public function handle(
        RequestInterface $request,
        ParametersInterface $configuration,
        ContextInterface $context,
    ): mixed {
        $payload = $request->getPayload();

        $result = $this->backend->post('/invoicing/invoices/create', [
            'customer'      => [
                'id'    => $payload->get('customer_id'),
                'email' => $payload->get('customer_email'),
                'name'  => $payload->get('customer_name'),
            ],
            'line_items'    => $payload->get('line_items'),
            'currency'      => $payload->get('currency') ?? 'USD',
            'due_days'      => $payload->get('due_days') ?? 30,
            'auto_collect'  => $payload->get('auto_collect') ?? false,
            'processor'     => $payload->get('processor'),
            'notes'         => $payload->get('notes'),
            'created_by'    => $context->getUser()->getId(),
        ]);

        return $this->responseFactory->create(
            statusCode: $result['status'],
            payload: $result['body'],
        );
    }
}
