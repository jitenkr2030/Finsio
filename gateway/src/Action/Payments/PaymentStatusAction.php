<?php

declare(strict_types=1);

namespace Finsio\Gateway\Action\Payments;

use Finsio\Gateway\Connector\DjangoBackendConnector;
use Fusio\Engine\ActionAbstract;
use Fusio\Engine\ContextInterface;
use Fusio\Engine\ParametersInterface;
use Fusio\Engine\RequestInterface;

/**
 * GET /api/v1/payments/{payment_id}
 *
 * Returns the current status and details of a payment.
 *
 * Path Parameters:
 *   - payment_id  UUID of the payment
 *
 * Response includes: status, processor, amount, currency,
 * external_id, redirect_url, paid_at, created_at.
 *
 * Scopes: payment, admin
 */
final class PaymentStatusAction extends ActionAbstract
{
    public function __construct(
        private readonly DjangoBackendConnector $backend,
    ) {}

    public function handle(
        RequestInterface $request,
        ParametersInterface $configuration,
        ContextInterface $context,
    ): mixed {
        $paymentId = $request->getUriFragments()->get('payment_id');

        $result = $this->backend->get("/payments/{$paymentId}");

        return $this->responseFactory->create(
            statusCode: $result['status'],
            payload: $result['body'],
        );
    }
}
