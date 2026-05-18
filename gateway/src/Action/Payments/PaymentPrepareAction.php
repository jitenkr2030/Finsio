<?php

declare(strict_types=1);

namespace Finsio\Gateway\Action\Payments;

use Finsio\Gateway\Connector\DjangoBackendConnector;
use Fusio\Engine\ActionAbstract;
use Fusio\Engine\ContextInterface;
use Fusio\Engine\ParametersInterface;
use Fusio\Engine\RequestInterface;

/**
 * POST /api/v1/payments/prepare
 *
 * Prepares a new payment transaction through the unified payment layer.
 * The Django backend orchestrates getpaid-core's PaymentFlow, selects
 * the optimal processor, and returns a redirect URL or form payload.
 *
 * POST body:
 *   - amount        (required) Amount in major units (e.g. 49.99)
 *   - currency      (optional) ISO 4217 code, default USD
 *   - processor     (optional) Preferred processor slug
 *   - customer_id   (required) Customer identifier
 *   - customer_email(required) Customer email
 *   - description   (optional) Payment description
 *   - reference     (optional) Invoice or order reference
 *   - callback_url  (optional) URL to redirect after payment
 *
 * Scopes: payment, admin
 */
final class PaymentPrepareAction extends ActionAbstract
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

        $result = $this->backend->post('/payments/prepare', [
            'amount'         => $payload->get('amount'),
            'currency'       => $payload->get('currency') ?? 'USD',
            'processor'      => $payload->get('processor'),
            'customer'       => [
                'id'    => $payload->get('customer_id'),
                'email' => $payload->get('customer_email'),
            ],
            'description'    => $payload->get('description'),
            'reference'      => $payload->get('reference'),
            'callback_url'   => $payload->get('callback_url'),
            'created_by'     => $context->getUser()->getId(),
        ]);

        return $this->responseFactory->create(
            statusCode: $result['status'],
            payload: $result['body'],
        );
    }
}
