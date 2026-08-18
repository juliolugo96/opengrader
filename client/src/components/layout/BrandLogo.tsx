import Image from "next/image";

import horizontalLogo from "../../../assets/logos/horizontal-lookup.png";
import stackedLogo from "../../../assets/logos/stacked.png";

export function BrandWordmark() {
  return (
    <Image
      alt="OpenGrader"
      className="h-auto w-full"
      priority
      sizes="176px"
      src={horizontalLogo}
    />
  );
}

export function BrandMark() {
  return (
    <Image
      alt=""
      aria-hidden="true"
      className="size-full object-contain"
      priority
      sizes="40px"
      src={stackedLogo}
    />
  );
}
