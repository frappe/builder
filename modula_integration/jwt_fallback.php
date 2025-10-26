<?php

/**
 * JWT Fallback Implementation
 *
 * Lightweight JWT encoder/decoder for shared hosting environments
 * where Composer packages may not be available.
 *
 * Supports: HS256, HS384, HS512
 *
 * Note: For production, use firebase/php-jwt when possible.
 * This is a fallback for restricted environments only.
 */

class JWT_Fallback
{
    private static $supported_algs = [
        'HS256' => 'sha256',
        'HS384' => 'sha384',
        'HS512' => 'sha512',
    ];

    /**
     * Encode a payload to JWT
     *
     * @param array $payload
     * @param string $key Secret key
     * @param string $alg Algorithm (HS256, HS384, HS512)
     * @return string JWT token
     */
    public static function encode(array $payload, string $key, string $alg = 'HS256'): string
    {
        if (!isset(self::$supported_algs[$alg])) {
            throw new Exception("Algorithm {$alg} not supported");
        }

        // Create header
        $header = [
            'typ' => 'JWT',
            'alg' => $alg
        ];

        // Encode segments
        $segments = [
            self::urlsafeB64Encode(json_encode($header)),
            self::urlsafeB64Encode(json_encode($payload))
        ];

        // Create signature
        $signing_input = implode('.', $segments);
        $signature = self::sign($signing_input, $key, $alg);
        $segments[] = self::urlsafeB64Encode($signature);

        return implode('.', $segments);
    }

    /**
     * Decode a JWT
     *
     * @param string $jwt JWT token
     * @param string $key Secret key
     * @param string $alg Expected algorithm
     * @return array Decoded payload
     * @throws Exception
     */
    public static function decode(string $jwt, string $key, string $alg = 'HS256'): array
    {
        $segments = explode('.', $jwt);

        if (count($segments) !== 3) {
            throw new Exception('Invalid JWT: Wrong number of segments');
        }

        list($headb64, $bodyb64, $cryptob64) = $segments;

        // Decode header
        $header = json_decode(self::urlsafeB64Decode($headb64), true);
        if (!$header) {
            throw new Exception('Invalid JWT: Invalid header encoding');
        }

        // Verify algorithm
        if (!isset($header['alg']) || $header['alg'] !== $alg) {
            throw new Exception('Invalid JWT: Algorithm mismatch');
        }

        // Decode payload
        $payload = json_decode(self::urlsafeB64Decode($bodyb64), true);
        if (!$payload) {
            throw new Exception('Invalid JWT: Invalid payload encoding');
        }

        // Verify signature
        $sig = self::urlsafeB64Decode($cryptob64);
        $signing_input = "{$headb64}.{$bodyb64}";

        if (!self::verify($signing_input, $sig, $key, $alg)) {
            throw new Exception('Invalid JWT: Signature verification failed');
        }

        // Check expiration
        if (isset($payload['exp']) && $payload['exp'] < time()) {
            throw new Exception('Invalid JWT: Token has expired');
        }

        // Check not before
        if (isset($payload['nbf']) && $payload['nbf'] > time()) {
            throw new Exception('Invalid JWT: Token not yet valid');
        }

        return $payload;
    }

    /**
     * Sign a string
     *
     * @param string $msg Message to sign
     * @param string $key Secret key
     * @param string $alg Algorithm
     * @return string Signature
     */
    private static function sign(string $msg, string $key, string $alg): string
    {
        $hash_alg = self::$supported_algs[$alg];
        return hash_hmac($hash_alg, $msg, $key, true);
    }

    /**
     * Verify a signature
     *
     * @param string $msg Message
     * @param string $signature Signature to verify
     * @param string $key Secret key
     * @param string $alg Algorithm
     * @return bool
     */
    private static function verify(string $msg, string $signature, string $key, string $alg): bool
    {
        $expected = self::sign($msg, $key, $alg);

        // Use hash_equals to prevent timing attacks
        if (function_exists('hash_equals')) {
            return hash_equals($signature, $expected);
        }

        // Fallback for older PHP versions
        return $signature === $expected;
    }

    /**
     * URL-safe Base64 encode
     *
     * @param string $data
     * @return string
     */
    private static function urlsafeB64Encode(string $data): string
    {
        return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
    }

    /**
     * URL-safe Base64 decode
     *
     * @param string $data
     * @return string
     */
    private static function urlsafeB64Decode(string $data): string
    {
        $remainder = strlen($data) % 4;
        if ($remainder) {
            $padlen = 4 - $remainder;
            $data .= str_repeat('=', $padlen);
        }
        return base64_decode(strtr($data, '-_', '+/'));
    }
}
