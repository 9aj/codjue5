#include "CodMapTeleport.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/Controller.h"
#include "TimerManager.h"

bool UCodMapTeleportSubsystem::Claim(APawn* Pawn, double Until)
{
    for (auto It = LockedUntil.CreateIterator(); It; ++It)
        if (!It.Key().IsValid() || It.Value() <= GetWorld()->GetTimeSeconds()) It.RemoveCurrent();
    if (LockedUntil.Contains(Pawn)) return false;
    LockedUntil.Add(Pawn, Until);
    return true;
}

void UCodMapTeleportSubsystem::Release(APawn* Pawn) { LockedUntil.Remove(Pawn); }

ACodMapTeleport::ACodMapTeleport()
{
    PrimaryActorTick.bCanEverTick = false;
    bReplicates = true;
    TriggerMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TriggerMesh"));
    SetRootComponent(TriggerMesh);
    TriggerMesh->SetCollisionProfileName(TEXT("Trigger"));
    TriggerMesh->SetGenerateOverlapEvents(true);
    TriggerMesh->SetHiddenInGame(true);
    TriggerMesh->SetCastShadow(false);
}

void ACodMapTeleport::BeginPlay()
{
    Super::BeginPlay();
    TriggerMesh->OnComponentBeginOverlap.AddDynamic(this, &ACodMapTeleport::OnOverlap);
}

void ACodMapTeleport::OnOverlap(UPrimitiveComponent*, AActor* OtherActor,
    UPrimitiveComponent*, int32, bool, const FHitResult&)
{
    APawn* Pawn = Cast<APawn>(OtherActor);
    if (!Pawn || !HasAuthority()) return;
    auto* Locks = GetWorld()->GetSubsystem<UCodMapTeleportSubsystem>();
    if (!Locks->Claim(Pawn, GetWorld()->GetTimeSeconds() + DelaySeconds + FMath::Max(0.05f, CooldownSeconds))) return;
    if (DelaySeconds <= 0) { Transport(Pawn); return; }
    FTimerHandle Handle;
    GetWorldTimerManager().SetTimer(Handle, FTimerDelegate::CreateWeakLambda(this,
        [this, WeakPawn = TWeakObjectPtr<APawn>(Pawn)] { Transport(WeakPawn); }), DelaySeconds, false);
}

void ACodMapTeleport::Transport(TWeakObjectPtr<APawn> WeakPawn)
{
    APawn* Pawn = WeakPawn.Get();
    if (!Pawn) return;
    auto* Locks = GetWorld()->GetSubsystem<UCodMapTeleportSubsystem>();
    if (!TriggerMesh->IsOverlappingActor(Pawn)) { Locks->Release(Pawn); return; }
    FVector Location = Destination;
    if (bSourceOriginAtFeet)
        if (auto* Capsule = Pawn->FindComponentByClass<UCapsuleComponent>()) Location.Z += Capsule->GetScaledCapsuleHalfHeight();
    if (!Pawn->TeleportTo(Location, bSetView ? DestinationRotation : Pawn->GetActorRotation()))
    { Locks->Release(Pawn); return; }
    if (bSetView && Pawn->GetController()) Pawn->GetController()->SetControlRotation(DestinationRotation);
}
