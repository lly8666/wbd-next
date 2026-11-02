package faketcp
// Pinned upstream generic Go packet/association tests retain their independent
// historical test vectors; never installed in the actual product binary.
// Historical MSS option vectors for pinned original Go unit tests ONLY.
// The real product has no DefaultMSS symbol or 1360B fallback.
const DefaultMSS uint16 = 1360
func init(){_ =SetPublicV4AdvertisedMSS(DefaultMSS)}
