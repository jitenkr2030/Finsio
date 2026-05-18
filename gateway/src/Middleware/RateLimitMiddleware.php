<?php

declare(strict_types=1);

namespace Finsio\Gateway\Middleware;

use Psr\Http\Message\ResponseInterface;
use Psr\Http\Message\ServerRequestInterface;
use Psr\Http\Server\MiddlewareInterface;
use Psr\Http\Server\RequestHandlerInterface;

/**
 * Rate Limiting Middleware for Fusio gateway.
 *
 * Enforces per-client rate limits using a sliding window algorithm.
 * Limits are determined by the client's subscription plan:
 *   - Free:       100 requests/hour
 *   - Growth:     5,000 requests/hour
 *   - Enterprise: 50,000 requests/hour
 *
 * Rate limit info is returned in response headers:
 *   X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
 */
final class RateLimitMiddleware implements MiddlewareInterface
{
    private const PLAN_LIMITS = [
        'free'       => ['rate' => 100,   'timespan' => 3600],
        'growth'     => ['rate' => 5000,  'timespan' => 3600],
        'enterprise' => ['rate' => 50000, 'timespan' => 3600],
    ];

    private const DEFAULT_LIMIT = ['rate' => 60, 'timespan' => 3600];

    public function __construct(
        private readonly \Redis $redis,
    ) {}

    public function process(
        ServerRequestInterface $request,
        RequestHandlerInterface $handler,
    ): ResponseInterface {
        $clientId = $this->resolveClientId($request);
        $plan = $request->getAttribute('user_plan', 'free');
        $limit = self::PLAN_LIMITS[$plan] ?? self::DEFAULT_LIMIT;

        $key = sprintf('ratelimit:%s:%s', $clientId, date('Y-m-d-H'));
        $current = (int) $this->redis->get($key);

        if ($current >= $limit['rate']) {
            $ttl = $this->redis->ttl($key);
            $response = new \Nyholm\Psr7\Response(429);
            $response->getBody()->write(json_encode([
                'error'   => 'rate_limit_exceeded',
                'message' => sprintf(
                    'Rate limit of %d requests/hour exceeded. Resets in %d seconds.',
                    $limit['rate'],
                    max($ttl, 0),
                ),
            ]));

            return $response
                ->withHeader('Content-Type', 'application/json')
                ->withHeader('X-RateLimit-Limit', (string) $limit['rate'])
                ->withHeader('X-RateLimit-Remaining', '0')
                ->withHeader('X-RateLimit-Reset', (string) (time() + max($ttl, 0)))
                ->withHeader('Retry-After', (string) max($ttl, 60));
        }

        // Increment counter
        $newCount = $this->redis->incr($key);
        if ($newCount === 1) {
            $this->redis->expire($key, $limit['timespan']);
        }

        $response = $handler->handle($request);

        // Attach rate limit headers
        $remaining = max($limit['rate'] - $newCount, 0);
        return $response
            ->withHeader('X-RateLimit-Limit', (string) $limit['rate'])
            ->withHeader('X-RateLimit-Remaining', (string) $remaining)
            ->withHeader('X-RateLimit-Reset', (string) (time() + $limit['timespan']));
    }

    private function resolveClientId(ServerRequestInterface $request): string
    {
        $userId = $request->getAttribute('user_id');
        if ($userId) {
            return 'user:' . $userId;
        }

        $forwarded = $request->getHeaderLine('X-Forwarded-For');
        if ($forwarded) {
            return 'ip:' . explode(',', $forwarded)[0];
        }

        $serverParams = $request->getServerParams();
        return 'ip:' . ($serverParams['REMOTE_ADDR'] ?? 'unknown');
    }
}
