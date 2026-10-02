#if WITH_DEV_AUTOMATION_TESTS
#include "CodMapTeleport.h"
#include "Misc/AutomationTest.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/WorldSettings.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCodMapTeleportTest, "CodMapRuntime.Teleport.DelayAndFeet",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FCodMapTeleportTest::RunTest(const FString&)
{
    const UWorld::InitializationValues Values = UWorld::InitializationValues().AllowAudioPlayback(false)
        .CreatePhysicsScene(true).RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, NAME_None, nullptr, true,
        ERHIFeatureLevel::Num, &Values);
    FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
    Context.SetCurrentWorld(World);
    ACodMapTeleport* Portal = World->SpawnActor<ACodMapTeleport>();
    Portal->TriggerMesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")));
    Portal->TriggerMesh->SetWorldScale3D(FVector(4));
    Portal->Destination = FVector(1000, 0, 100);
    Portal->DelaySeconds = 0.1f;
    APawn* Pawn = World->SpawnActor<APawn>();
    UCapsuleComponent* Capsule = NewObject<UCapsuleComponent>(Pawn);
    Pawn->SetRootComponent(Capsule);
    Capsule->InitCapsuleSize(20, 40);
    Capsule->SetCollisionProfileName(TEXT("Pawn"));
    Capsule->SetGenerateOverlapEvents(true);
    Capsule->RegisterComponent();
    Pawn->SetActorLocation(FVector(500, 0, 0));
    World->InitializeActorsForPlay(FURL());
    World->BeginPlay();
    World->GetWorldSettings()->NotifyBeginPlay();
    World->GetWorldSettings()->NotifyMatchStarted();
    TestTrue(TEXT("Portal begins play"), Portal->HasActorBegunPlay());
    Pawn->SetActorLocation(FVector::ZeroVector);
    Capsule->UpdateOverlaps();
    TestTrue(TEXT("Pawn overlaps source volume"), Portal->TriggerMesh->IsOverlappingActor(Pawn));
    auto Tick = [World]() { ++GFrameCounter; World->Tick(LEVELTICK_All, 0.03f); };
    Tick();
    TestTrue(TEXT("Delay retains pawn at source"), Pawn->GetActorLocation().Equals(FVector::ZeroVector, 1));
    for (int Index = 0; Index < 10; ++Index) Tick();
    AddInfo(FString::Printf(TEXT("Pawn destination: %s"), *Pawn->GetActorLocation().ToString()));
    TestTrue(TEXT("Teleport applies destination plus capsule feet offset"), Pawn->GetActorLocation().Equals(FVector(1000, 0, 140), 1));
    // Another entry during the shared cooldown must not transport the pawn.
    Pawn->SetActorLocation(FVector::ZeroVector);
    Capsule->UpdateOverlaps();
    for (int Index = 0; Index < 4; ++Index) Tick();
    TestTrue(TEXT("Cooldown suppresses immediate reentry"), Pawn->GetActorLocation().Equals(FVector::ZeroVector, 1));
    World->EndPlay(EEndPlayReason::Quit);
    GEngine->DestroyWorldContext(World);
    World->DestroyWorld(false);
    return true;
}
#endif
